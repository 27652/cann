"""Serial, leased CAModel targeted strict INT32 checks in isolated directories."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'optimization'))
from camodel_resource import lease
from int32_golden import reference

binary = HERE / 'bench-build/bench_mix_2d'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
results = HERE / 'results/conditional-strict-v1'
summaries = []
with lease() as fd:
    results.mkdir(parents=True, exist_ok=False)
    for shape in ((2, 16384, 33), (3, 16385, 17), (2, 8193, 33)):
        m, n, k = shape
        work = results / 'x'.join(map(str, shape))
        (work / 'input').mkdir(parents=True)
        (work / 'output').mkdir()
        (work / 'logs').mkdir()
        rng = np.random.default_rng(20261017)
        a = rng.integers(-128, 128, (m, k), dtype=np.int8)
        b = rng.integers(-128, 128, (n, k), dtype=np.int8)
        s = rng.uniform(.001, .1, m).astype(np.float32)
        t = rng.uniform(.001, .1, n).astype(np.float32)
        # Include a deterministic zero row and signed scales when possible.
        a[0] = 0
        s[1::3] *= -1
        t[::2] *= -1
        for name, array in zip(('x1', 'x2', 'x1Scale', 'x2Scale'), (a, b, s, t)):
            array.tofile(work / 'input' / (name + '.bin'))
        expected, scale, _ = reference(a, b, s, t)
        expected.tofile(work / 'output/golden_y.bin')
        scale.tofile(work / 'output/golden_yScale.bin')
        env = dict(os.environ, CAMODEL_LEASE_FD=str(fd),
                   CAMODEL_LOG_PATH=str(work / 'logs'), STARS_LOG_PATH=str(work / 'logs'))
        fingerprint = {'shape': shape, 'seed': 20261017,
                       'source_sha256': sha(HERE / 'kernel.asc'), 'binary_sha256': sha(binary),
                       'runner_sha256': sha(Path(__file__)),
                       'golden_script_sha256': sha(ROOT / 'optimization/int32_golden.py'),
                       'files': {str(p.relative_to(work)): sha(p) for p in work.rglob('*.bin')},
                       'environment': {key: env.get(key, '') for key in (
                           'ASCEND_HOME_PATH', 'CAMODEL_HOME', 'CAMODEL_PATH', 'LD_LIBRARY_PATH')}}
        (work / 'fingerprint.json').write_text(json.dumps(fingerprint, indent=2) + '\n')
        with (work / 'run.log').open('w') as log:
            process = subprocess.Popen([str(binary), *map(str, shape)], cwd=work,
                                       env=env, stdout=log, stderr=subprocess.STDOUT,
                                       pass_fds=(fd,), start_new_session=True)
            try:
                rc = process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=15)
                (work / 'failure.json').write_text(json.dumps({'status': 'timeout'}))
                raise
        assert rc == 0, f'CAModel exit {rc}, see {work}'
        y = np.fromfile(work / 'output/y.bin', np.int8).reshape(m, n)
        ys = np.fromfile(work / 'output/yScale.bin', np.float32).reshape(m)
        diff = np.abs(ys - scale)
        relative = diff / np.maximum(np.abs(scale), np.finfo(np.float32).tiny)
        summary = {'shape': shape, 'int8_mismatches': int(np.count_nonzero(y != expected)),
                   'scale_ok': bool(np.allclose(ys, scale, rtol=1e-4, atol=1e-4)),
                   'scale_max_abs_diff': float(diff.max()),
                   'scale_max_rel_diff': float(relative.max()),
                   'scale_rtol': 1e-4, 'scale_atol': 1e-4,
                   'status': 'finished', 'fingerprint': fingerprint}
        (work / 'result.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps({k: v for k, v in summary.items() if k != 'fingerprint'}), flush=True)
        assert summary['int8_mismatches'] == 0 and summary['scale_ok'], f'strict mismatch: {work}'
        summaries.append(summary)
(results / 'summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
