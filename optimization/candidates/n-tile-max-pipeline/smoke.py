"""Leased strict INT32 early-max smoke, explicit probe dispatch recorded."""
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

p = argparse.ArgumentParser()
p.add_argument('--run-id', required=True)
p.add_argument('--shape', nargs=3, type=int, default=(17, 4097, 33))
p.add_argument('--probe', action='store_true')
args = p.parse_args()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
binary = HERE / ('build/bench_n_tile_probe' if args.probe else 'build/bench_n_tile')
with lease() as fd:
    work = HERE / 'results' / args.run_id
    work.mkdir(parents=True, exist_ok=False)
    for name in ('input', 'output', 'logs'):
        (work / name).mkdir()
    m, n, k = args.shape
    rng = np.random.default_rng(20261017)
    a = rng.integers(-128, 128, (m, k), dtype=np.int8)
    b = rng.integers(-128, 128, (n, k), dtype=np.int8)
    s = rng.uniform(.001, .1, m).astype(np.float32)
    t = rng.uniform(.001, .1, n).astype(np.float32)
    a[0] = 0
    s[1::3] *= -1
    t[::2] *= -1
    for name, value in zip(('x1', 'x2', 'x1Scale', 'x2Scale'), (a, b, s, t)):
        value.tofile(work / 'input' / (name + '.bin'))
    yr, sr, _ = reference(a, b, s, t)
    yr.tofile(work / 'output/golden_y.bin')
    sr.tofile(work / 'output/golden_yScale.bin')
    env = dict(os.environ, CAMODEL_LEASE_FD=str(fd),
               CAMODEL_LOG_PATH=str(work / 'logs'), STARS_LOG_PATH=str(work / 'logs'))
    fingerprint = dict(shape=args.shape, seed=20261017, probe_min_rows=17 if args.probe else 1024,
        probe_core_cap=1 if args.probe else None,
        source_sha256=sha(HERE / 'kernel.asc'), binary_sha256=sha(binary),
        runner_sha256=sha(Path(__file__)), golden_sha256=sha(ROOT / 'optimization/int32_golden.py'),
        input_hashes={x.name: sha(x) for x in (work / 'input').iterdir()},
        environment={key: env.get(key, '') for key in
                     ('ASCEND_HOME_PATH', 'LD_LIBRARY_PATH', 'ASCEND_SOC_VERSION')})
    (work / 'fingerprint.json').write_text(json.dumps(fingerprint, indent=2) + '\n')
    with (work / 'run.log').open('w') as log:
        proc = subprocess.Popen([str(binary), *map(str, args.shape)], cwd=work, env=env,
            stdout=log, stderr=subprocess.STDOUT, pass_fds=(fd,), start_new_session=True)
        try:
            rc = proc.wait(timeout=240)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=15)
            (work / 'failure.json').write_text(json.dumps({'status': 'timeout'}))
            raise
    if rc:
        (work / 'failure.json').write_text(json.dumps({'status': 'runtime_failure', 'exit_code': rc}))
        raise RuntimeError(f'exit {rc}: {work}/run.log')
    y = np.fromfile(work / 'output/y.bin', np.int8).reshape(m, n)
    scale = np.fromfile(work / 'output/yScale.bin', np.float32)
    diff = np.abs(scale - sr)
    result = dict(shape=args.shape, int8_mismatches=int(np.count_nonzero(y != yr)),
        scale_ok=bool(np.allclose(scale, sr, rtol=1e-4, atol=1e-4)),
        scale_max_abs_diff=float(diff.max()),
        scale_max_rel_diff=float((diff / np.maximum(np.abs(sr), np.finfo(np.float32).tiny)).max()),
        rtol=1e-4, atol=1e-4)
    (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
    assert result['int8_mismatches'] == 0 and result['scale_ok']
