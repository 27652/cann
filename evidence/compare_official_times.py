#!/usr/bin/env python3
"""Offline per-testcase timing feedback, never a score/promotion decision."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def compare(baseline, candidate):
    if not baseline.get('contest_id') or not baseline.get('problem_id'):
        raise ValueError('missing baseline context')
    for key in ('contest_id', 'problem_id'):
        if baseline[key] != candidate.get(key):
            raise ValueError('context mismatch: ' + key)
    if not baseline.get('submission_id') or not candidate.get('submission_id'):
        raise ValueError('missing submission ID')
    if baseline['submission_id'] == candidate['submission_id']:
        raise ValueError('same submission')

    def cases(record):
        if record.get('status') != 'Pass' or record.get('valid') is False:
            raise ValueError('submission not passing')
        rows = record.get('testcases', [])
        if len(rows) != 15:
            raise ValueError('expected 15 testcases')
        mapped = {}
        for row in rows:
            key = row.get('testcase_id')
            time = row.get('time')
            if not key or key in mapped or row.get('testcase_status') != 'Pass':
                raise ValueError('invalid/duplicate/nonpassing testcase')
            if isinstance(time, bool) or not isinstance(time, (int, float)):
                raise ValueError('nonnumeric time')
            if not math.isfinite(time) or time <= 0:
                raise ValueError('nonpositive/nonfinite time')
            mapped[key] = time
        return mapped

    b, c = cases(baseline), cases(candidate)
    if b.keys() != c.keys():
        raise ValueError('testcase ID mismatch')
    rows = []
    for key, old in b.items():
        new = c[key]
        rows.append({'testcase_id': key, 'baseline_time': old, 'candidate_time': new,
                     'delta_time': new - old, 'relative_change_percent': (new / old - 1) * 100})
    return {'baseline_submission_id': baseline['submission_id'],
            'candidate_submission_id': candidate['submission_id'],
            'contest_id': baseline['contest_id'], 'problem_id': baseline['problem_id'],
            'interpretation': 'Timing feedback only; not an official score or promotion decision. '
                              'Positive delta means slower. Shape mapping and repeatability unknown.',
            'time_unit': 'server time field; not independently inferred',
            'faster_cases': sum(r['delta_time'] < 0 for r in rows),
            'slower_cases': sum(r['delta_time'] > 0 for r in rows),
            'equal_cases': sum(r['delta_time'] == 0 for r in rows),
            'testcases': rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', required=True, type=Path)
    p.add_argument('--candidate', required=True, type=Path)
    p.add_argument('--baseline-observed-at', required=True)
    p.add_argument('--candidate-observed-at', required=True)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    result = compare(json.loads(args.baseline.read_text()), json.loads(args.candidate.read_text()))
    result['sources'] = {label: {'path': str(path),
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'observed_at': when}
                         for label, path, when in (
                             ('baseline', args.baseline, args.baseline_observed_at),
                             ('candidate', args.candidate, args.candidate_observed_at))}
    # Refuse overwriting an earlier comparison.
    with args.output.open('x') as out:
        out.write(json.dumps(result, indent=2) + '\n')
    print('| testcase ID | baseline | candidate | delta | change |')
    print('|---|---:|---:|---:|---:|')
    for r in result['testcases']:
        print(f"| {r['testcase_id']} | {r['baseline_time']:.2f} | {r['candidate_time']:.2f} | "
              f"{r['delta_time']:+.2f} | {r['relative_change_percent']:+.2f}% |")
    print(f"Faster {result['faster_cases']}, slower {result['slower_cases']}, equal {result['equal_cases']}.")


if __name__ == '__main__':
    main()
