"""Hash/ownership checks and optional serial strict device probes."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'optimization'))
p = argparse.ArgumentParser()
p.add_argument('--smoke', choices=('dual-aiv-fixed', 'l0c-chunk64-probe'))
p.add_argument('--run-id', default='strict-v1')
args = p.parse_args()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for name in ('dual-aiv-fixed', 'l0c-chunk64-probe'):
    dest = HERE / name
    for filename, digest in json.loads((dest / 'project-hashes.json').read_text()).items():
        assert sha(dest / 'submit-project' / filename) == digest
count = 0
for m in (1, 2, 3, 7, 16, 17, 31, 65, 129, 1025):
    for blocks in range(1, 33):
        seen = Counter()
        for raw in range(blocks):
            for sub in range(2):
                logical = raw * 2 + sub
                first, end = m * logical // (blocks * 2), m * (logical+1) // (blocks * 2)
                assert 0 <= first <= end <= m
                seen.update(range(first, end))
        assert seen == Counter({i: 1 for i in range(m)})
        count += 1
print(json.dumps({'hashes_ok': True, 'ownership_cases': count}), flush=True)
if not args.smoke:
    sys.exit(0)

import numpy as np
from camodel_resource import lease
from int32_golden import reference
assert Path(args.run_id).name == args.run_id
candidate = HERE / args.smoke
results = candidate / 'results' / args.run_id
results.mkdir(parents=True, exist_ok=False)
shapes = {'dual-aiv-fixed': ((17, 513, 65), (2, 33, 129), (65, 257, 33)),
          'l0c-chunk64-probe': ((2, 33, 129), (17, 257, 193))}[args.smoke]
summaries = []
with lease() as fd:
    for m, n, k in shapes:
        work = results / f'{m}x{n}x{k}'
        for d in ('input', 'output', 'logs'):
            (work / d).mkdir(parents=True)
        rng = np.random.default_rng(20261017)
        a = rng.integers(-128, 128, (m, k), dtype=np.int8)
        b = rng.integers(-128, 128, (n, k), dtype=np.int8)
        s = rng.uniform(.001, .1, m).astype(np.float32)
        t = rng.uniform(.001, .1, n).astype(np.float32)
        a[0] = 0
        s[1::3] *= -1
        t[::2] *= -1
        for filename, array in zip(('x1', 'x2', 'x1Scale', 'x2Scale'), (a, b, s, t)):
            array.tofile(work / 'input' / (filename + '.bin'))
        y_ref, ys_ref, _ = reference(a, b, s, t)
        y_ref.tofile(work / 'output/golden_y.bin')
        ys_ref.tofile(work / 'output/golden_yScale.bin')
        binary = candidate / 'bench-build/bench_probe'
        env = dict(os.environ, CAMODEL_LEASE_FD=str(fd), CAMODEL_LOG_PATH=str(work / 'logs'),
                   STARS_LOG_PATH=str(work / 'logs'))
        fingerprint = {'shape': [m, n, k], 'seed': 20261017,
            'source': sha(candidate / 'submit-project/kernel.asc'), 'binary': sha(binary),
            'runner': sha(Path(__file__)), 'golden': sha(ROOT / 'optimization/int32_golden.py'),
            'input': {f.name: sha(f) for f in (work / 'input').iterdir()},
            'environment': {key: env.get(key, '') for key in (
                'ASCEND_HOME_PATH', 'LD_LIBRARY_PATH', 'ASCEND_SOC_VERSION')}}
        (work / 'fingerprint.json').write_text(json.dumps(fingerprint, indent=2) + '\n')
        with (work / 'run.log').open('w') as log:
            proc = subprocess.Popen([str(binary), str(m), str(n), str(k)], cwd=work,
                env=env, stdout=log, stderr=subprocess.STDOUT, pass_fds=(fd,), start_new_session=True)
            try:
                rc = proc.wait(timeout=240)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=20)
                (work / 'failure.json').write_text(json.dumps({'status': 'timeout'}))
                raise
        if rc:
            (work / 'failure.json').write_text(json.dumps({'status': 'runtime_failure', 'exit_code': rc}))
            raise RuntimeError(f'exit {rc}: {work}')
        y = np.fromfile(work / 'output/y.bin', np.int8).reshape(m, n)
        ys = np.fromfile(work / 'output/yScale.bin', np.float32)
        diff = np.abs(ys - ys_ref)
        result = {'shape': [m, n, k], 'int8_mismatches': int(np.count_nonzero(y != y_ref)),
            'scale_ok': bool(np.allclose(ys, ys_ref, rtol=1e-4, atol=1e-4)),
            'scale_max_abs_diff': float(diff.max()),
            'scale_max_rel_diff': float((diff / np.maximum(np.abs(ys_ref), np.finfo(np.float32).tiny)).max()),
            'rtol': 1e-4, 'atol': 1e-4}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
        assert result['int8_mismatches'] == 0 and result['scale_ok']
        summaries.append(result)
(results / 'summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
