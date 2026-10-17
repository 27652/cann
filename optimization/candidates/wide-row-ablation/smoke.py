"""Run identical strict INT32 cases for isolated ablations under one lease."""
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

SHAPES = ((2, 8192, 65), (3, 8193, 33), (17, 513, 65))
VARIANTS = ('baseline', 'vector-only', 'ancillary-only')
hashes = json.loads((HERE / 'source-hashes.json').read_text())
result_root = HERE / 'results/strict-v1'

with lease() as fd:
    result_root.mkdir(parents=True, exist_ok=False)
    for variant in VARIANTS:
        binary = HERE / variant / 'bench-build/bench_ablation'
        summaries = []
        for shape in SHAPES:
            m, n, k = shape
            work = result_root / variant / 'x'.join(map(str, shape))
            (work / 'input').mkdir(parents=True)
            (work / 'output').mkdir()
            (work / 'logs').mkdir()
            rng = np.random.default_rng(20261017)
            a = rng.integers(-128, 128, (m, k), dtype=np.int8)
            b = rng.integers(-128, 128, (n, k), dtype=np.int8)
            s = rng.uniform(.001, .1, m).astype(np.float32)
            t = rng.uniform(.001, .1, n).astype(np.float32)
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
            fingerprint = {'variant': variant, 'shape': shape, 'seed': 20261017,
                           'source_sha256': hashes[variant],
                           'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                           'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           'golden_sha256': hashlib.sha256((ROOT / 'optimization/int32_golden.py').read_bytes()).hexdigest(),
                           'environment': {key: env.get(key, '') for key in (
                               'ASCEND_HOME_PATH', 'CAMODEL_HOME', 'CAMODEL_PATH', 'LD_LIBRARY_PATH')}}
            (work / 'fingerprint.json').write_text(json.dumps(fingerprint, indent=2) + '\n')
            with (work / 'run.log').open('w') as log:
                proc = subprocess.Popen([str(binary), *map(str, shape)], cwd=work, env=env,
                                        stdout=log, stderr=subprocess.STDOUT,
                                        pass_fds=(fd,), start_new_session=True)
                try:
                    rc = proc.wait(timeout=180)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=15)
                    raise RuntimeError(f'timeout: {variant} {shape}')
            assert rc == 0, f'CAModel exit {rc}: {variant} {shape}; see {work}'
            y = np.fromfile(work / 'output/y.bin', np.int8).reshape(m, n)
            ys = np.fromfile(work / 'output/yScale.bin', np.float32).reshape(m)
            diff = np.abs(ys - scale)
            rel = diff / np.maximum(np.abs(scale), np.finfo(np.float32).tiny)
            summary = {'variant': variant, 'shape': shape,
                       'int8_mismatches': int(np.count_nonzero(y != expected)),
                       'scale_ok': bool(np.allclose(ys, scale, rtol=1e-4, atol=1e-4)),
                       'scale_max_abs_diff': float(diff.max()),
                       'scale_max_rel_diff': float(rel.max()),
                       'fingerprint': fingerprint}
            (work / 'result.json').write_text(json.dumps(summary, indent=2) + '\n')
            print(json.dumps({k: v for k, v in summary.items() if k != 'fingerprint'}), flush=True)
            assert summary['int8_mismatches'] == 0 and summary['scale_ok'], summary
            summaries.append(summary)
        (result_root / f'{variant}-summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
