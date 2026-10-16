#!/usr/bin/env python3
"""Opt-in real CAModel scheduler acceptance using an existing Case 1 binary.

Never compiles, submits formally, or removes results. Only the Worker started
by this script is killed in the crash test; its model is allowed to finish.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from camodel_resource import unmanaged_processes, lease
from camodel_scheduler import Scheduler, sha256

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / 'optimization/camodel_scheduler.py'
ENV_KEYS = ('PATH', 'LD_LIBRARY_PATH', 'PYTHONPATH', 'HOME', 'LANG',
            'ASCEND_HOME_PATH', 'ASCEND_TOOLKIT_HOME', 'ASCEND_OPP_PATH',
            'ASCEND_AICPU_PATH', 'ASCEND_SOC_VERSION', 'CAMODEL_LIB_DIR',
            'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS')


def wait_for(predicate, seconds=300):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(.01)
    raise TimeoutError('acceptance condition was not reached')


def model_pids(snapshot):
    expected = str(Path(snapshot) / 'candidate/optimization/build/bench_optimized')
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            args = (proc / 'cmdline').read_bytes().split(b'\0')
            if args and args[0].decode(errors='replace') == expected:
                found.append(int(proc.name))
        except OSError:
            pass
    return found


def run(toolkit, parent):
    if unmanaged_processes():
        raise RuntimeError('existing model/benchmark detected; acceptance not started')
    with lease():
        pass
    base = Path(tempfile.mkdtemp(prefix='scheduler-acceptance-', dir=parent))
    print(f'Acceptance evidence: {base}', flush=True)
    summary = {'run_dir': str(base), 'stages': {}, 'kind': 'local scheduler acceptance',
               'official_submission': False}
    summary_path = base / 'acceptance.json'
    workers = []
    s = Scheduler(base / 'queue')
    candidate = base / 'worktree-copy'
    files = ['kernel.asc', 'optimization/build/bench_optimized',
             'optimization/benchmark.py', 'optimization/int32_golden.py',
             'optimization/camodel_resource.py', 'optimization/test_points.json']
    for name in files:
        target = candidate / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    # Vendor initialization only; simulator compatibility links are private to
    # this run, rather than rewriting the project's shared .runtime directory.
    capture = 'import os,json; print(json.dumps({k:os.environ[k] for k in ' + repr(ENV_KEYS) + ' if k in os.environ}))'
    raw = subprocess.check_output(['bash', '-c', 'source "$1"; python3 -c "$2"',
                                   'acceptance-env', str(toolkit / 'set_env.sh'), capture], text=True)
    env = json.loads(raw)
    lib = toolkit / 'tools/simulator/Ascend910B1/lib'
    runtime = base / 'runtime'
    runtime.mkdir()
    for link, target in [('libruntime.so', 'libruntime_camodel.so'),
                         ('libascend_hal.so', 'libnpu_drv.so')]:
        if not (lib / target).is_file():
            raise FileNotFoundError(lib / target)
        (runtime / link).symlink_to(lib / target)
    env.update(LD_LIBRARY_PATH=f'{runtime}:{lib}:' + env.get('LD_LIBRARY_PATH', ''),
               ASCEND_SOC_VERSION='Ascend910B1', CAMODEL_LIB_DIR=str(lib),
               OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    summary['identity'] = {name: sha256(candidate / name) for name in files}

    def save():
        summary_path.write_text(json.dumps(summary, indent=2) + '\n')

    def submit(label):
        start = time.monotonic()
        task = s.submit(command=['python3', 'optimization/benchmark.py', '--case-ids', '1',
                                 '--variants', 'optimized'], cwd=candidate,
                        result_dir=base / 'results' / label,
                        binds=[candidate / name for name in files], env=env, timeout=300,
                        metadata={'candidate_id': label, 'source_sha256': sha256(candidate / 'kernel.asc'),
                                  'binary_sha256': sha256(candidate / 'optimization/build/bench_optimized'),
                                  'case': 1, 'variant': 'optimized', 'golden_mode': 'int32-primary+fp32-diagnostic',
                                  'environment_fingerprint': {'soc': 'Ascend910B1',
                                      'toolkit': str(toolkit), 'set_env_sha256': sha256(toolkit / 'set_env.sh')}})
        summary.setdefault('submissions', []).append({'label': label, 'task_id': task['task_id'],
                                                     'elapsed_seconds': time.monotonic() - start})
        save()
        return task

    def worker(label):
        log = base / f'worker-{label}.log'
        with log.open('w') as out:
            proc = subprocess.Popen([sys.executable, str(CLI), '--root', str(s.root), 'worker', '--once'],
                                    stdout=out, stderr=subprocess.STDOUT)
        workers.append(proc)
        return proc, log

    def completed(task):
        state = next(t for t in s.list_tasks() if t['task_id'] == task['task_id'])
        assert state['status'] == 'passed', state
        path = Path(task['result_dir']) / 'benchmark/case01_1x1x1_boundary/optimized/result.json'
        result = json.loads(path.read_text())
        assert result['int32_mismatches'] == 0 and result['int32_scale_ok'], result
        assert result['fingerprint']['source_sha256'] == task['metadata']['source_sha256']
        assert result['binary_sha256'] == task['metadata']['binary_sha256']
        return {'task_id': task['task_id'], 'result_path': str(path),
                'int32_mismatches': result['int32_mismatches'],
                'int32_scale_ok': result['int32_scale_ok'],
                'task_cycles': result['task_cycles'], 'total_ticks': result['total_ticks']}

    try:
        one = submit('single')
        p, _ = worker('single')
        assert p.wait(timeout=320) == 0
        summary['stages']['single'] = completed(one)
        save()

        first = submit('competition-first')
        p, _ = worker('competition-first')
        active = wait_for(lambda: model_pids(first['snapshot_dir']), 60)
        second = submit('competition-second')
        # Change only this run's staging copy, not root or frozen source. The
        # queued task must retain the original source hash and executable.
        with (candidate / 'kernel.asc').open('a') as out:
            out.write('\n// acceptance: modified staging source after enqueue\n')
        challenger, log = worker('competition-challenger')
        assert challenger.wait(timeout=30) == 0
        refusal = json.loads(log.read_text())
        assert refusal.get('busy'), refusal
        assert next(t for t in s.list_tasks() if t['task_id'] == second['task_id'])['status'] == 'queued'
        assert not model_pids(second['snapshot_dir'])
        assert p.wait(timeout=320) == 0
        first_result = completed(first)
        p, _ = worker('competition-second')
        assert p.wait(timeout=320) == 0
        summary['stages']['competition'] = {'active_model_pids': active, 'refusal': refusal,
                                            'first': first_result, 'second': completed(second),
                                            'staging_source_changed': True, 'queued_snapshot_preserved': True}
        save()

        crash = submit('crash-first')
        p, _ = worker('crash-first')
        active = wait_for(lambda: model_pids(crash['snapshot_dir']), 60)
        # Sole deliberately terminated process: the exact Worker Popen object
        # created above. The model and runner remain alive and finish normally.
        p.kill()
        p.wait(timeout=10)
        surviving = model_pids(crash['snapshot_dir'])
        assert surviving, 'model finished before crash check; test inconclusive'
        later = submit('crash-successor')
        challenger, log = worker('crash-challenger')
        assert challenger.wait(timeout=30) == 0
        refusal = json.loads(log.read_text())
        assert refusal.get('busy'), refusal
        assert not model_pids(later['snapshot_dir'])
        wait_for(lambda: not model_pids(crash['snapshot_dir']), 320)
        # Also wait for the surviving benchmark to release the inherited lease.
        def resource_available():
            try:
                with lease():
                    return True
            except RuntimeError:
                return False
        wait_for(resource_available, 30)
        p, _ = worker('crash-successor')
        assert p.wait(timeout=320) == 0
        orphan = next(t for t in s.list_tasks() if t['task_id'] == crash['task_id'])
        assert orphan['status'] == 'failed', orphan
        summary['stages']['crash'] = {'terminated_worker_pid': workers[-3].pid,
                                      'surviving_model_pids': surviving, 'refusal': refusal,
                                      'orphan_status': orphan['status'], 'successor': completed(later)}
        summary['passed'] = True
        save()
    except BaseException as exc:
        summary.update(passed=False, error=repr(exc))
        save()
        # Do not terminate model processes on an assertion failure. Wait for
        # the bounded tasks this run started and preserve all evidence.
        for proc in workers:
            if proc.poll() is None:
                proc.wait(timeout=330)
        raise
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real-camodel', action='store_true', required=True)
    parser.add_argument('--toolkit', type=Path, required=True)
    parser.add_argument('--parent', type=Path, default=Path('/tmp/opencode'))
    args = parser.parse_args()
    run(args.toolkit.resolve(), args.parent.resolve())
