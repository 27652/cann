"""Deterministic host layout/ownership checks; optional serial strict smoke."""
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
parser.add_argument('--candidate', default='a-l1-group4-stride16',
                    choices=('baseline', 'a-l1-group4-stride16'))
parser.add_argument('--shape', default='17x1025x64')
parser.add_argument('--run-id', default='strict-v1')
args = parser.parse_args()
candidate = HERE / args.candidate
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
hashes = json.loads((candidate / 'project-hashes.json').read_text())
assert hashes == {p.relative_to(candidate / 'submit-project').as_posix(): sha(p)
                  for p in (candidate / 'submit-project').rglob('*') if p.is_file()}
count = 0
for m in (1, 2, 16, 17, 65, 129, 1025):
    for n in (257, 513, 1024, 1025, 4097):
        for blocks in (1, 2, 8, 20, 24):
            mt, nt = (m + 15) // 16, (n + 255) // 256
            tasks = mt * ((nt + 3) // 4)
            tiles = [(t % mt, ni) for b in range(blocks)
                     for t in range(b, tasks, blocks)
                     for ni in range((t // mt) * 4, min((t // mt) * 4 + 4, nt))]
            assert sorted(tiles) == [(mi, ni) for mi in range(mt) for ni in range(nt)]
            spans = [(m*b // (2*blocks), m*(b+1) // (2*blocks)) for b in range(2*blocks)]
            assert [r for first, end in spans for r in range(first, end)] == list(range(m))
            count += 1
# NZ A panel layout: each K/32 block holds 16 rows of 32 bytes.
for k in (32, 64, 256, 4096):
    offsets = [(ki // 32) * 16 * 32 + mi * 32 + ki % 32
               for mi in range(16) for ki in range(k)]
    assert sorted(offsets) == list(range(16*k))
    assert max(offsets) < 65536
print(json.dumps({'ownership_configurations': count, 'project_hashes_ok': True,
                  'nz_model_ok': True}), flush=True)
if not args.smoke:
    sys.exit(0)

import numpy as np
from camodel_resource import lease
from int32_golden import reference

shape = tuple(map(int, args.shape.split('x')))
assert len(shape) == 3 and min(shape) > 0
m, n, k = shape
binary = candidate / 'bench-build/bench_l1'
assert binary.is_file()
work = candidate / 'results' / args.run_id / args.shape
with lease() as fd:
    for directory in ('input', 'output', 'logs'):
        (work / directory).mkdir(parents=True, exist_ok=False)
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
    yr, sr, _ = reference(a, b, s, t)
    yr.tofile(work / 'output/golden_y.bin')
    sr.tofile(work / 'output/golden_yScale.bin')
    env = dict(os.environ, CAMODEL_LEASE_FD=str(fd), CAMODEL_LOG_PATH=str(work / 'logs'),
               STARS_LOG_PATH=str(work / 'logs'))
    fingerprint = {'shape': shape, 'seed': 20261017, 'project_hashes': hashes,
        'binary_sha256': sha(binary), 'runner_sha256': sha(Path(__file__)),
        'golden_sha256': sha(ROOT / 'optimization/int32_golden.py'),
        'input_hashes': {p.name: sha(p) for p in (work / 'input').iterdir()},
        'cmake_sha256': sha(candidate / 'CMakeLists.txt'),
        'cmake_cache_sha256': sha(candidate / 'bench-build/CMakeCache.txt'),
        'environment': {key: env.get(key, '') for key in (
            'ASCEND_HOME_PATH', 'LD_LIBRARY_PATH', 'PATH', 'ASCEND_SOC_VERSION')}}
    (work / 'fingerprint.json').write_text(json.dumps(fingerprint, indent=2) + '\n')
    with (work / 'run.log').open('w') as log:
        proc = subprocess.Popen([str(binary), *map(str, shape)], cwd=work, env=env,
            stdout=log, stderr=subprocess.STDOUT, pass_fds=(fd,), start_new_session=True)
        try:
            rc = proc.wait(timeout=300)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=15)
            (work / 'failure.json').write_text(json.dumps({'status': 'timeout'}))
            raise
    if rc:
        (work / 'failure.json').write_text(json.dumps({'status': 'runtime_failure', 'exit_code': rc}))
        raise RuntimeError(f'exit {rc}; see {work}/run.log')
    y = np.fromfile(work / 'output/y.bin', np.int8).reshape(m, n)
    ys = np.fromfile(work / 'output/yScale.bin', np.float32)
    diff = np.abs(ys - sr)
    result = {'shape': shape, 'int8_mismatches': int(np.count_nonzero(y != yr)),
        'scale_ok': bool(np.allclose(ys, sr, rtol=1e-4, atol=1e-4)),
        'scale_max_abs_diff': float(diff.max()),
        'scale_max_rel_diff': float((diff / np.maximum(np.abs(sr), np.finfo(np.float32).tiny)).max()),
        'rtol': 1e-4, 'atol': 1e-4}
    (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
    assert result['int8_mismatches'] == 0 and result['scale_ok']
