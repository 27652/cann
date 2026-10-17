#!/usr/bin/env python3
"""Validate one completed queue pair without running or polling CAModel."""
import argparse
import json
import math
from pathlib import Path

from camodel_scheduler import Scheduler


COMMON = ('input_sha256', 'int32_golden_sha256', 'fp32_golden_sha256',
          'benchmark_sha256', 'int32_golden_script_sha256',
          'test_points_sha256', 'environment', 'shape', 'mode', 'case_id', 'variant')


def compare(tasks, results):
    if len(tasks) != 2 or len(results) != 2:
        raise ValueError('expected two tasks and two results')
    for task, result in zip(tasks, results):
        if task.get('status') != 'passed' or task.get('returncode') != 0:
            raise ValueError('task has not passed: ' + task['task_id'])
        fp = result['fingerprint']
        for key in ('source_sha256', 'binary_sha256'):
            if fp[key] != task['metadata'][key]:
                raise ValueError('identity mismatch: ' + key)
        if result['binary_sha256'] != fp['binary_sha256']:
            raise ValueError('result binary identity mismatch')
        if result['int32_mismatches'] != 0 or result['int32_scale_ok'] is not True:
            raise ValueError('strict INT32 validation failed')
        for key in ('task_cycles', 'total_ticks'):
            value = result[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError('invalid metric: ' + key)
    if tasks[0]['env'] != tasks[1]['env']:
        raise ValueError('task environment differs')
    for key in COMMON:
        if results[0]['fingerprint'][key] != results[1]['fingerprint'][key]:
            raise ValueError('common fingerprint differs: ' + key)
    a, b = results
    return {
        'valid_pair': True,
        'baseline_task_id': tasks[0]['task_id'],
        'candidate_task_id': tasks[1]['task_id'],
        'baseline': a, 'candidate': b,
        'delta': {k: {'absolute': b[k] - a[k],
                      'percent': 100 * (b[k] / a[k] - 1)}
                  for k in ('task_cycles', 'total_ticks')},
        'scope': 'local diagnostic only; not official score or promotion',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    states = {t['task_id']: t for t in Scheduler(args.root).list_tasks()}
    try:
        tasks = [states[args.baseline], states[args.candidate]]
        results = []
        for task in tasks:
            paths = list((Path(task['result_dir']) / 'benchmark').rglob('result.json'))
            if len(paths) != 1:
                raise ValueError('expected exactly one case result: ' + task['task_id'])
            results.append(json.loads(paths[0].read_text()))
        out = compare(tasks, results)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        out = {'valid_pair': False, 'reason': str(exc)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k not in ('baseline', 'candidate')}))
    return 0 if out['valid_pair'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
