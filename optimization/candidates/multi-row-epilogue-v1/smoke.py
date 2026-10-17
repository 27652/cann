"""Serial strict INT32 paired smoke; never reuse an existing result directory."""
import argparse
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

parser = argparse.ArgumentParser()
parser.add_argument('--run-id', required=True)
parser.add_argument('--rows', nargs='+', type=int, default=[1, 4])
parser.add_argument('--case', choices=['tail', 'half', 'aligned', 'wide'], default='tail')
args = parser.parse_args()
results = HERE / 'results' / args.run_id
results.mkdir(parents=True, exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
shape = {'tail': (129, 513, 65), 'half': (193, 17, 33),
         'aligned': (17, 1024, 33), 'wide': (17, 1025, 33)}[args.case]
m, n, k = shape
rng = np.random.default_rng(20261017)
a = rng.integers(-128, 128, (m, k), dtype=np.int8)
b = rng.integers(-128, 128, (n, k), dtype=np.int8)
s = rng.uniform(.001, .1, m).astype(np.float32)
t = rng.uniform(.001, .1, n).astype(np.float32)
if args.case == 'half':
    a.fill(0); b.fill(0)
    a[:, 0] = 1; b[:, 0] = 1; s.fill(1)
    t[:] = (np.arange(n, dtype=np.float32) % 127) + np.float32(.5)
    t[-1] = 127
else:
    a[::11] = 0
    s[1::3] *= -1
    t[::2] *= -1
expected, scale, _ = reference(a, b, s, t)
summaries = []
with lease() as fd:
    for rows in args.rows:
        binary = HERE / f'build/bench_rows{rows}'
        work = results / f'rows{rows}'
        for directory in ('input', 'output', 'logs'):
            (work / directory).mkdir(parents=True)
        for name, value in zip(('x1', 'x2', 'x1Scale', 'x2Scale'), (a, b, s, t)):
            value.tofile(work / 'input' / (name + '.bin'))
        expected.tofile(work / 'output/golden_y.bin')
        scale.tofile(work / 'output/golden_yScale.bin')
        env = dict(os.environ, CAMODEL_LEASE_FD=str(fd),
                   CAMODEL_LOG_PATH=str(work / 'logs'), STARS_LOG_PATH=str(work / 'logs'))
        fingerprint = {'shape': shape, 'rows': rows, 'seed': 20261017,
                       'source_sha256': sha(HERE / 'kernel.asc'),
                       'binary_sha256': sha(binary), 'runner_sha256': sha(Path(__file__)),
                       'cmake_sha256': sha(HERE / 'CMakeLists.txt'),
                       'golden_sha256': sha(ROOT / 'optimization/int32_golden.py'),
                       'files': {str(p.relative_to(work)): sha(p) for p in work.rglob('*.bin')},
                       'environment': {key: env.get(key, '') for key in (
                           'ASCEND_HOME_PATH', 'CAMODEL_HOME', 'CAMODEL_PATH', 'LD_LIBRARY_PATH')}}
        (work / 'fingerprint.json').write_text(json.dumps(fingerprint, indent=2) + '\n')
        with (work / 'run.log').open('w') as log:
            process = subprocess.Popen([str(binary), *map(str, shape)], cwd=work,
                                       env=env, stdout=log, stderr=subprocess.STDOUT,
                                       pass_fds=(fd,), start_new_session=True)
            try:
                rc = process.wait(timeout=240)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=15)
                (work / 'failure.json').write_text('{"status":"timeout"}\n')
                raise
        if rc:
            (work / 'failure.json').write_text(json.dumps({'returncode': rc}) + '\n')
            raise RuntimeError(f'CAModel exit {rc}: {work}')
        y = np.fromfile(work / 'output/y.bin', np.int8).reshape(m, n)
        ys = np.fromfile(work / 'output/yScale.bin', np.float32).reshape(m)
        diff = np.abs(ys - scale)
        result = {'shape': shape, 'rows': rows,
                  'int8_mismatches': int(np.count_nonzero(y != expected)),
                  'scale_ok': bool(np.allclose(ys, scale, rtol=1e-4, atol=1e-4)),
                  'scale_max_abs_diff': float(diff.max()),
                  'scale_max_rel_diff': float((diff / np.maximum(np.abs(scale), np.finfo(np.float32).tiny)).max()),
                  'scale_rtol': 1e-4, 'scale_atol': 1e-4, 'fingerprint': fingerprint}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k != 'fingerprint'}), flush=True)
        summaries.append(result)
        (results / 'summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
        assert result['int8_mismatches'] == 0 and result['scale_ok'], f'strict mismatch: {work}'
