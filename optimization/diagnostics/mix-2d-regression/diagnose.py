"""Frozen paired whole-kernel CAModel diagnostics; never maps official IDs to shapes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'optimization'))
from camodel_resource import lease
from int32_golden import reference


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    bench = (ROOT / 'optimization/candidates/mix-2d-single-launch/bench.asc').read_bytes()
    old = (ROOT / 'evidence/formal/fast-track-6ad2e531/source/kernel.asc').read_bytes()
    new = (ROOT / 'evidence/formal/mix-2d-single-launch-6ad2ed99/source/kernel.asc').read_bytes()
    needle = b'const uint32_t tileM = std::min(64U,'
    assert new.count(needle) == 1
    tile16 = new.replace(needle, b'const uint32_t tileM = std::min(16U,')
    manifest = {}
    for name, source in [('baseline', old), ('current', new), ('tile16', tile16)]:
        dest = HERE / 'snapshots' / name
        dest.mkdir(parents=True, exist_ok=False)
        (dest / 'kernel.asc').write_bytes(source)
        (dest / 'bench.asc').write_bytes(bench)
        manifest[name] = {p.name: sha(p) for p in dest.iterdir()}
    (HERE / 'sources.json').write_text(json.dumps(manifest, indent=2) + '\n')


def run(run_id, shapes):
    results = HERE / 'results' / run_id
    results.mkdir(parents=True, exist_ok=False)
    summaries = []
    with lease() as fd:
        for shape in shapes:
            m, n, k = shape
            rng = np.random.default_rng(20261017)
            a = rng.integers(-128, 128, (m, k), dtype=np.int8)
            b = rng.integers(-128, 128, (n, k), dtype=np.int8)
            s = rng.uniform(.001, .1, m).astype(np.float32)
            t = rng.uniform(.001, .1, n).astype(np.float32)
            a[0] = 0
            s[1::3] *= -1
            t[::2] *= -1
            expected, scale, _ = reference(a, b, s, t)
            for variant in ('baseline', 'current', 'tile16'):
                work = results / 'x'.join(map(str, shape)) / variant
                for sub in ('input', 'output', 'logs'):
                    (work / sub).mkdir(parents=True)
                for name, array in zip(('x1', 'x2', 'x1Scale', 'x2Scale'), (a, b, s, t)):
                    array.tofile(work / 'input' / (name + '.bin'))
                expected.tofile(work / 'output/golden_y.bin')
                scale.tofile(work / 'output/golden_yScale.bin')
                binary = HERE / 'build' / ('bench_' + variant)
                env = dict(os.environ, CAMODEL_LEASE_FD=str(fd),
                           CAMODEL_LOG_PATH=str(work / 'logs'), STARS_LOG_PATH=str(work / 'logs'))
                fingerprint = dict(shape=shape, seed=20261017, variant=variant,
                    source_sha256=sha(HERE / 'snapshots' / variant / 'kernel.asc'),
                    bench_sha256=sha(HERE / 'snapshots' / variant / 'bench.asc'),
                    binary_sha256=sha(binary), runner_sha256=sha(Path(__file__)),
                    golden_sha256=sha(ROOT / 'optimization/int32_golden.py'),
                    cmake_sha256=sha(HERE / 'CMakeLists.txt'),
                    environment={key: env.get(key, '') for key in (
                        'ASCEND_HOME_PATH', 'LD_LIBRARY_PATH', 'CAMODEL_HOME', 'CAMODEL_PATH')},
                    files={str(p.relative_to(work)): sha(p) for p in work.rglob('*.bin')})
                (work / 'fingerprint.json').write_text(json.dumps(fingerprint, indent=2) + '\n')
                with (work / 'run.log').open('w') as log:
                    proc = subprocess.Popen([str(binary), *map(str, shape)], cwd=work, env=env,
                        stdout=log, stderr=subprocess.STDOUT, pass_fds=(fd,), start_new_session=True)
                    try:
                        rc = proc.wait(timeout=240)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGTERM)
                        proc.wait(timeout=15)
                        (work / 'failure.json').write_text(json.dumps({'status': 'timeout'}))
                        raise
                if rc:
                    (work / 'failure.json').write_text(json.dumps({'status': 'error', 'returncode': rc}))
                    raise RuntimeError(f'{variant}: exit {rc}; see {work}')
                y = np.fromfile(work / 'output/y.bin', np.int8).reshape(m, n)
                ys = np.fromfile(work / 'output/yScale.bin', np.float32)
                task = (work / 'logs/profile_task_log0.toml').read_text()
                duration = re.search(r'^\s*duration\s*=\s*(\d+)', task, re.M)
                ticks = re.search(r'Total tick: (\d+)', (work / 'run.log').read_text())
                assert duration, f'no duration: {work}'
                diff = np.abs(ys - scale)
                record = dict(shape=shape, variant=variant, status='finished',
                    int8_mismatches=int(np.count_nonzero(y != expected)),
                    scale_ok=bool(np.allclose(ys, scale, rtol=1e-4, atol=1e-4)),
                    scale_max_abs_diff=float(diff.max()),
                    scale_max_rel_diff=float((diff / np.maximum(np.abs(scale), np.finfo(np.float32).tiny)).max()),
                    scale_rtol=1e-4, scale_atol=1e-4, task_cycles=int(duration[1]),
                    total_ticks=int(ticks[1]) if ticks else None, fingerprint=fingerprint)
                (work / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
                summaries.append(record)
                (results / 'summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
                print(json.dumps({key: value for key, value in record.items() if key != 'fingerprint'}), flush=True)
                assert record['int8_mismatches'] == 0 and record['scale_ok'], f'strict failure: {work}'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--run-id')
    parser.add_argument('--shapes', nargs='+', default=['64x256x256', '64x1024x256', '16x1024x256'])
    args = parser.parse_args()
    if args.prepare:
        prepare()
    else:
        if not args.run_id:
            parser.error('--run-id required without --prepare')
        run(args.run_id, [tuple(map(int, value.split('x'))) for value in args.shapes])
