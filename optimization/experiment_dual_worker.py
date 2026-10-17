#!/usr/bin/env python3
"""Host-only two-process scheduler compatibility experiment; never runs CAModel."""
import argparse
import functools
import json
import multiprocessing
from pathlib import Path
import tempfile
import time

from camodel_resource import lease
from camodel_scheduler import Scheduler, sha256


def consume(root, lock, gate, output, count):
    scheduler = Scheduler(Path(root), resource_lease=functools.partial(
        lease, lock_path=Path(lock), check_legacy=False))
    gate.wait(10)
    busy = 0
    completed = []
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        result = scheduler.worker_once()
        if result and result.get('busy'):
            busy += 1
        elif result:
            completed.append(result)
        tasks = scheduler.list_tasks()
        if len(tasks) == count and all(t['status'] in ('passed', 'failed', 'timeout') for t in tasks):
            break
        time.sleep(.005)
    Path(output).write_text(json.dumps({'busy_count': busy, 'completed': completed}))


def run(parent):
    base = Path(tempfile.mkdtemp(prefix='dual-worker-host-', dir=parent))
    summary = {'kind': 'host-only dual Worker compatibility', 'real_camodel': False,
               'official_submission': False, 'run_dir': str(base), 'scenarios': {}}
    for scenario in ('shared-queue', 'separate-queues'):
        folder = base / scenario
        candidate = folder / 'candidate'
        candidate.mkdir(parents=True)
        source = candidate / 'kernel.asc'
        source.write_text('// host-only placeholder; not compiled\n')
        script = candidate / 'host_task.py'
        script.write_text(
            'import json,os,time\nfrom pathlib import Path\n'
            'start=time.monotonic_ns()\ntime.sleep(.06)\n'
            'Path("interval.json").write_text(json.dumps({"pid":os.getpid(),'
            '"start":start,"end":time.monotonic_ns()}))\n')
        lock = folder / 'isolated-host.lock'
        make = lambda root: Scheduler(root, resource_lease=functools.partial(
            lease, lock_path=lock, check_legacy=False))
        roots = [folder / 'queue-a', folder / ('queue-a' if scenario == 'shared-queue' else 'queue-b')]
        schedulers = [make(root) for root in roots]
        tasks = []
        for i in range(12):
            tasks.append(schedulers[i % 2].submit(
                command=['python3', 'host_task.py'], cwd=candidate,
                result_dir=folder / 'results' / str(i), binds=[source, script],
                env={}, timeout=5, metadata={'candidate_id': f'host-{i}',
                    'source_sha256': sha256(source), 'binary_sha256': sha256(script),
                    'case': i, 'variant': 'host-mock', 'golden_mode': 'not-applicable-host-only',
                    'environment_fingerprint': {'kind': 'host-only', 'script_sha256': sha256(script)}}))
        gate = multiprocessing.Event()
        workers = [multiprocessing.Process(target=consume, args=(
            str(roots[i]), str(lock), gate, str(folder / f'worker-{i}.json'),
            12 if scenario == 'shared-queue' else 6)) for i in range(2)]
        for worker in workers:
            worker.start()
        gate.set()
        for worker in workers:
            worker.join(40)
            if worker.is_alive() or worker.exitcode != 0:
                raise RuntimeError(f'host Worker did not finish successfully: {worker.pid}')
        reports = [json.loads((folder / f'worker-{i}.json').read_text()) for i in range(2)]
        states = {t['task_id']: t for scheduler in schedulers for t in scheduler.list_tasks()}
        executed = [r['task_id'] for report in reports for r in report['completed']]
        intervals = sorted((json.loads((Path(t['frozen_cwd']) / 'interval.json').read_text())
                            for t in tasks), key=lambda x: x['start'])
        checks = {
            'all_12_passed': len(states) == 12 and all(t['status'] == 'passed' and t['returncode'] == 0 for t in states.values()),
            'exactly_once': len(executed) == 12 and len(set(executed)) == 12 and set(executed) == set(states),
            'no_execution_overlap': all(a['end'] <= b['start'] for a, b in zip(intervals, intervals[1:])),
            'busy_observed': sum(report['busy_count'] for report in reports) > 0,
            'isolated_results': len({t['result_dir'] for t in states.values()}) == 12,
        }
        summary['scenarios'][scenario] = {'checks': checks, 'workers': reports, 'intervals': intervals,
                                          'worker_pids': [p.pid for p in workers]}
    summary['passed'] = all(all(s['checks'].values()) for s in summary['scenarios'].values())
    summary['implementation_sha256'] = {name: sha256(Path(__file__).parent / name)
        for name in ('experiment_dual_worker.py', 'camodel_scheduler.py', 'camodel_resource.py')}
    (base / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'run_dir': str(base), 'passed': summary['passed'],
                      'checks': {k: v['checks'] for k, v in summary['scenarios'].items()}}, indent=2))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, default=Path('/tmp/opencode'))
    args = parser.parse_args()
    raise SystemExit(run(args.parent))
