"""Host-only scheduler tests. No CANN runtime or CAModel executable is used."""
import functools
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from camodel_resource import lease
from camodel_scheduler import Scheduler, sha256


def test_lease(path):
    return functools.partial(lease, lock_path=Path(path), check_legacy=False)


def worker(root, lock):
    Scheduler(Path(root), resource_lease=test_lease(lock)).worker_once()


class SchedulerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='scheduler-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.cwd = self.base / 'worktree'
        self.cwd.mkdir()
        self.source = self.cwd / 'kernel.asc'
        self.source.write_text('candidate-v1')
        self.script = self.cwd / 'experiment.py'
        self.script.write_text('print("ok")\n')
        self.lock = self.base / 'host.lock'
        self.scheduler = Scheduler(self.base / 'queue', resource_lease=test_lease(self.lock))
        self.counter = 0

    def submit(self, script=None, scheduler=None, **overrides):
        if script is not None:
            self.script.write_text(script)
        self.counter += 1
        spec = dict(command=[sys.executable, 'experiment.py'], cwd=self.cwd,
                    result_dir=self.base / f'result-{self.counter}',
                    binds=[self.source, self.script], env={}, timeout=5,
                    metadata={'candidate_id': f'test-{self.counter}',
                              'source_sha256': sha256(self.source),
                              'binary_sha256': sha256(self.script),
                              'case': 1, 'variant': 'mock', 'golden_mode': 'int32',
                              'environment_fingerprint': {'kind': 'host-only mock'}})
        # System Python is a runtime dependency, not a submitted build artifact.
        spec['command'] = ['python3', 'experiment.py']
        spec.update(overrides)
        return (scheduler or self.scheduler).submit(**spec)

    def test_cross_queue_mutual_exclusion(self):
        marker = self.base / 'started'
        first = self.submit(f'import time\nfrom pathlib import Path\nPath({str(marker)!r}).touch()\ntime.sleep(.6)\n')
        other = Scheduler(self.base / 'other-queue', resource_lease=test_lease(self.lock))
        second = self.submit('print("second")\n', scheduler=other)
        proc = multiprocessing.Process(target=worker, args=(str(self.scheduler.root), str(self.lock)))
        proc.start()
        self.addCleanup(lambda: proc.is_alive() and proc.kill())
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(marker.exists())
        self.assertTrue(other.worker_once()['busy'])
        self.assertEqual(other.list_tasks()[0]['status'], 'queued')
        proc.join(5)
        self.assertEqual(proc.exitcode, 0)
        self.assertEqual(self.scheduler.list_tasks()[0]['status'], 'passed')
        self.assertEqual(other.worker_once()['status'], 'passed')

    def test_duplicate_and_directory_collisions(self):
        task = self.submit()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.scheduler.submit(command=task['command'], cwd=self.cwd,
                                  result_dir=self.base / 'duplicate', binds=[self.source, self.script],
                                  env={}, timeout=5, metadata=task['metadata'])
        other = Scheduler(self.base / 'other', resource_lease=test_lease(self.lock))
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.submit(scheduler=other, result_dir=Path(task['result_dir']))
        with self.assertRaisesRegex(ValueError, 'forbidden'):
            self.submit(result_dir=self.base / 'optimization/results/new')

    def test_worktree_edits_do_not_change_snapshot(self):
        task = self.submit('from pathlib import Path\nassert Path("kernel.asc").read_text() == "candidate-v1"\n')
        self.source.write_text('candidate-v2')
        self.script.write_text('raise RuntimeError("must not execute live code")')
        self.assertEqual(self.scheduler.worker_once()['status'], 'passed')
        self.assertEqual(Path(task['binds'][0]['snapshot']).read_text(), 'candidate-v1')

    def test_tampered_or_missing_snapshot_fails_closed(self):
        task = self.submit()
        snapshot = Path(task['binds'][0]['snapshot'])
        snapshot.chmod(0o600)
        snapshot.write_text('tampered')
        self.assertIsNone(self.scheduler.worker_once())
        self.assertEqual(self.scheduler.list_tasks()[0]['status'], 'failed')
        task = self.submit()
        Path(task['binds'][0]['snapshot']).unlink()
        self.assertIsNone(self.scheduler.worker_once())
        self.assertEqual(self.scheduler.list_tasks()[-1]['status'], 'failed')

    def test_failure_timeout_cancel_and_lock_release(self):
        self.submit('raise SystemExit(3)\n')
        self.assertEqual(self.scheduler.worker_once()['status'], 'failed')
        self.submit('import time\ntime.sleep(10)\n', timeout=.05)
        self.assertEqual(self.scheduler.worker_once()['status'], 'timeout')
        task = self.submit()
        self.assertEqual(self.scheduler.cancel(task['task_id'])['status'], 'cancelled')
        self.submit('print("recovered")\n')
        self.assertEqual(self.scheduler.worker_once()['status'], 'passed')

    def test_orphan_running_task_recovered_only_after_lease_release(self):
        marker = self.base / 'child-pid'
        task = self.submit(f'import os,time\nfrom pathlib import Path\nPath({str(marker)!r}).write_text(str(os.getpid()))\ntime.sleep(1)\n')
        proc = multiprocessing.Process(target=worker, args=(str(self.scheduler.root), str(self.lock)))
        proc.start()
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(marker.exists())
        proc.kill()
        proc.join(5)
        self.assertTrue(self.scheduler.worker_once()['busy'])
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = self.scheduler.worker_once()
            if result is None:
                break
            time.sleep(.05)
        self.assertEqual(self.scheduler.list_tasks()[0]['status'], 'failed')

    def test_priority_and_cooperative_yield_at_case_boundary(self):
        marker = self.base / 'running'
        first = self.submit(
            f'import time\nfrom pathlib import Path\n'
            f'Path({str(marker)!r}).touch()\ntime.sleep(.6)\n')
        low = self.submit('print("low")\n')
        proc = multiprocessing.Process(target=worker,
                                       args=(str(self.scheduler.root), str(self.lock)))
        proc.start()
        self.addCleanup(lambda: proc.is_alive() and proc.kill())
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(marker.exists())
        high = self.submit('print("high")\n', priority=10)
        states = {t['task_id']: t for t in self.scheduler.list_tasks()}
        self.assertEqual(states[first['task_id']]['status'], 'running')
        self.assertTrue(states[first['task_id']]['yield_requested'])
        proc.join(5)
        self.assertEqual(proc.exitcode, 0)
        states = {t['task_id']: t for t in self.scheduler.list_tasks()}
        self.assertEqual(states[first['task_id']]['status'], 'passed')
        self.assertTrue(states[first['task_id']]['yielded'])
        self.assertEqual(states[low['task_id']]['status'], 'queued')
        self.assertEqual(states[high['task_id']]['status'], 'queued')
        self.assertEqual(self.scheduler.worker_once()['task_id'], high['task_id'])
        self.assertEqual(self.scheduler.worker_once()['task_id'], low['task_id'])

    def test_priority_fifo_validation_and_legacy_default(self):
        low = self.submit(priority=-1)
        first = self.submit(priority=3)
        second = self.submit(priority=3)
        self.assertEqual(self.scheduler.worker_once()['task_id'], first['task_id'])
        self.assertEqual(self.scheduler.worker_once()['task_id'], second['task_id'])
        self.assertEqual(self.scheduler.worker_once()['task_id'], low['task_id'])
        for invalid in (True, 1.5, 'high'):
            with self.assertRaisesRegex(ValueError, 'priority'):
                self.submit(priority=invalid)
        legacy = self.submit()
        with self.scheduler._locked_queue() as data:
            data['tasks'][legacy['task_id']].pop('priority')
        self.assertEqual(self.scheduler.worker_once()['status'], 'passed')

    def test_submit_cases_has_independent_priorities_and_snapshots(self):
        template = self.submit()
        self.scheduler.cancel(template['task_id'])
        tasks = self.scheduler.submit_cases(
            cases=[{'command': ['python3', 'experiment.py'], 'metadata': {'case': 2}},
                   {'command': ['python3', 'experiment.py'], 'metadata': {'case': 3},
                    'priority': 5}],
            result_dir=self.base / 'batch', cwd=self.cwd,
            binds=[self.source, self.script], env={}, timeout=5,
            metadata=template['metadata'])
        self.assertEqual([t['metadata']['case'] for t in tasks], [2, 3])
        self.script.write_text('raise SystemExit(9)')
        self.assertEqual(self.scheduler.worker_once()['task_id'], tasks[1]['task_id'])
        self.assertEqual(self.scheduler.worker_once()['task_id'], tasks[0]['task_id'])
        self.assertTrue(all(t['status'] in ('passed', 'cancelled')
                            for t in self.scheduler.list_tasks()))


if __name__ == '__main__':
    unittest.main()
