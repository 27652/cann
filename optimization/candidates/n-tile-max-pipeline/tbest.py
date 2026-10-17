"""Compare immutable official bundle timings; no credentials or score estimates."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
paths = [ROOT / 'evidence/formal' / name / 'evidence.json' for name in
         ('tile-fifo-6ad335a8', 'dual-aiv-fixed-6ad33b78')]
fifo, current = [json.loads(path.read_text()) for path in paths]
old = {case['testcase_id']: case for case in fifo['testcases']}
lines = ['# Current official baseline versus TBest', '',
         f"Baseline submission: `{current['submission_id']}`, official score 19.45.",
         'Source: `evidence/formal/dual-aiv-fixed-6ad33b78/evidence.json`.',
         'TBest is best_time from that same stored official response, not a fresh query.',
         'Order below is baseline official testcase order; shapes are unknown.',
         'Times are microseconds. TBest need not be from one runnable submission.', '',
         '| Point | Testcase ID | FIFO | Dual AIV | Delta | Change | TBest | Dual/TBest |',
         '|---:|---|---:|---:|---:|---:|---:|---:|']
for i, case in enumerate(current['testcases'], 1):
    before = old[case['testcase_id']]['time']
    now, best = case['time'], case['best_time']
    lines.append(f"| {i} | `{case['testcase_id']}` | {before:.2f} | {now:.2f} | "
                 f"{now-before:+.2f} | {100*(now/before-1):+.2f}% | {best:.2f} | {now/best:.2f}x |")
lines += ['', 'No inferred aggregate score, shape assignment, or stage bottleneck.',
          'New submissions without attributable score must be compared by testcase ID',
          'against this verified baseline; timings alone cannot trigger promotion.', '']
(HERE / 'TBEST.md').write_text('\n'.join(lines))
print('\n'.join(lines))
