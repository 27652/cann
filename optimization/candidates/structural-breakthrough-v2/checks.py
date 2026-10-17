"""Static qualification, and optionally serial strict simulator smoke."""
import argparse
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
parser = argparse.ArgumentParser()
parser.add_argument('--smoke', action='store_true')
args = parser.parse_args()
count = 0
for m in (1, 2, 7, 16, 17, 31, 65, 129, 1025):
    for blocks in range(1, 33):
        spans = [(m * (2*b+s) // (2*blocks), m * (2*b+s+1) // (2*blocks))
                 for b in range(blocks) for s in range(2)]
        assert [r for first, end in spans for r in range(first, end)] == list(range(m))
        count += 1
for name in ('dual-aiv', 'ub-resident-8192'):
    candidate = HERE / name
    hashes = json.loads((candidate / 'project-hashes.json').read_text())
    for path, digest in hashes.items():
        assert hashlib.sha256((candidate / 'submit-project' / path).read_bytes()).hexdigest() == digest
    source = (candidate / 'submit-project/kernel.asc').read_text()
    assert 'FastExactQuantPrepared(numerator.u, scaleMantissa, scaleExponent, hint)' in source
    if name == 'ub-resident-8192':
        assert 'reduceWorkBuffer' not in source
        assert 'auto denominatorLocal = quantHalfBuffer.Get<float>();' in source
        assert 8192 * 23 + 1088 < 192 * 1024
print(json.dumps({'ownership_configurations': count, 'project_hashes_ok': True,
                  'ub_bytes': 8192 * 23 + 1088}))
if not args.smoke:
    sys.exit(0)

import numpy as np
from camodel_resource import lease
from int32_golden import reference
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
with lease() as fd:
    for name, shapes in (
        ('ub-resident-8192', ((2, 4097, 33), (2, 8192, 33), (2, 8201, 33))),
    ):
        candidate = HERE / name
        results = candidate / 'results/strict-smoke-v1'
        results.mkdir(parents=True, exist_ok=False)
        summaries = []
        for shape in shapes:
            m, n, k = shape
            work = results / 'x'.join(map(str, shape))
            for directory in ('input', 'output', 'logs'):
                (work / directory).mkdir(parents=True)
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
            binary = candidate / 'bench-build/bench_structural'
            env = dict(os.environ, CAMODEL_LEASE_FD=str(fd),
                       CAMODEL_LOG_PATH=str(work / 'logs'), STARS_LOG_PATH=str(work / 'logs'))
            fingerprint = {'shape': shape, 'seed': 20261017,
                'source_sha256': sha(candidate / 'submit-project/kernel.asc'),
                'binary_sha256': sha(binary), 'runner_sha256': sha(Path(__file__)),
                'golden_sha256': sha(ROOT / 'optimization/int32_golden.py'),
                'input_hashes': {p.name: sha(p) for p in (work / 'input').iterdir()},
                'environment': {key: env.get(key, '') for key in (
                    'ASCEND_HOME_PATH', 'LD_LIBRARY_PATH', 'ASCEND_SOC_VERSION')}}
            (work / 'fingerprint.json').write_text(json.dumps(fingerprint, indent=2) + '\n')
            with (work / 'run.log').open('w') as log:
                proc = subprocess.Popen([str(binary), *map(str, shape)], cwd=work, env=env,
                    stdout=log, stderr=subprocess.STDOUT, pass_fds=(fd,), start_new_session=True)
                try:
                    rc = proc.wait(timeout=180)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=15)
                    (work / 'failure.json').write_text(json.dumps({'status': 'timeout'}))
                    raise
            if rc:
                (work / 'failure.json').write_text(json.dumps({'status': 'runtime_failure', 'exit_code': rc}))
                raise RuntimeError(f'{name} exit {rc}; see {work}/run.log')
            y = np.fromfile(work / 'output/y.bin', np.int8).reshape(m, n)
            ys = np.fromfile(work / 'output/yScale.bin', np.float32)
            diff = np.abs(ys - ys_ref)
            result = {'shape': shape, 'int8_mismatches': int(np.count_nonzero(y != y_ref)),
                'scale_ok': bool(np.allclose(ys, ys_ref, rtol=1e-4, atol=1e-4)),
                'scale_max_abs_diff': float(diff.max()),
                'scale_max_rel_diff': float((diff / np.maximum(np.abs(ys_ref), np.finfo(np.float32).tiny)).max()),
                'rtol': 1e-4, 'atol': 1e-4}
            (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            print(name, json.dumps(result), flush=True)
            assert result['int8_mismatches'] == 0 and result['scale_ok']
            summaries.append(result)
        (results / 'summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
