#!/usr/bin/env python3
"""Run baseline and optimized binaries serially with isolated CAModel logs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parent

SUITE = [
    {"id": 1, "shape": [1, 1, 1], "profile": "boundary"},
    {"id": 2, "shape": [4, 8, 16], "profile": "random"},
    {"id": 3, "shape": [16, 16, 32], "profile": "random"},
    {"id": 4, "shape": [17, 33, 65], "profile": "random"},
    {"id": 5, "shape": [3, 7, 31], "profile": "zero_rows"},
    {"id": 6, "shape": [8, 17, 128], "profile": "signed_scale"},
    {"id": 7, "shape": [16, 256, 256], "profile": "random"},
    {"id": 8, "shape": [2, 1025, 32], "profile": "random"},
    {"id": 9, "shape": [2, 4097, 32], "profile": "zero_rows"},
    {"id": 10, "shape": [32, 65, 257], "profile": "extreme_int8"},
    {"id": 11, "shape": [129, 128, 256], "profile": "random"},
    {"id": 12, "shape": [1024, 256, 64], "profile": "random"},
    {"id": 13, "shape": [4, 64, 65536], "profile": "random"},
    {"id": 14, "shape": [2, 8, 131072], "profile": "extreme_int8"},
    {"id": 15, "shape": [16, 1024, 1024], "profile": "tiny_scale"},
]


def run_case(shape, variant, mode="random", resume=False, case_id=None, timeout=240):
    m, n, k = shape
    binary = ROOT / "build" / ("bench_" + variant)
    binary_hash = hashlib.sha256(binary.read_bytes()).hexdigest()
    label = (f"case{case_id:02d}_" if case_id is not None else "") + "x".join(map(str, shape)) + "_" + mode
    work = ROOT / "results" / label / variant
    if resume and (work / "result.json").exists():
        result = json.loads((work / "result.json").read_text())
        if result.get("binary_sha256") == binary_hash:
            print(json.dumps(result), flush=True)
            return result
    (work / "input").mkdir(parents=True, exist_ok=True)
    (work / "output").mkdir(exist_ok=True)
    logs = work / "logs"
    logs.mkdir(exist_ok=True)
    rng = np.random.default_rng(20261016 + (case_id or 0) * 1009)
    a = rng.integers(-128, 128, (m, k), dtype=np.int8)
    b = rng.integers(-128, 128, (n, k), dtype=np.int8)
    s = rng.uniform(.001, .1, m).astype(np.float32)
    t = rng.uniform(.001, .1, n).astype(np.float32)
    if mode == "zero":
        a[:] = 0
    elif mode == "zero_rows":
        a[::2] = 0
    elif mode in ("mixed", "signed_scale"):
        a[::3] = 0
        s[1::3] *= -1
        t[::2] *= -1
    elif mode == "boundary":
        a.fill(127); b.fill(-128); s.fill(1.0); t.fill(1.0)
    elif mode == "extreme_int8":
        a[::4] = 127; a[1::4] = -128
        b[::4] = -128; b[1::4] = 127
    elif mode == "tiny_scale":
        s[::2] = np.float32(1e-35); t[1::2] = np.float32(1e-35)
    elif mode == "half_boundary":
        # Each dot product is exactly 1, hence activation == channel scale.
        # Last channel fixes rowMax=127 and outputScale=1 exactly. Other
        # channels probe +/- 4 FP32 ULP around every half-integer threshold.
        a.fill(0); b.fill(0)
        a[:, 0] = 1; b[:, 0] = 1; s.fill(1.0)
        centers = (np.arange(n, dtype=np.float32) % 127) + np.float32(0.5)
        bits = centers.view(np.uint32).copy()
        delta = (np.arange(n) // 127) % 9 - 4
        t[:] = (bits.astype(np.int64) + delta).astype(np.uint32).view(np.float32)
        t[-1] = 127.0
    for name, value in zip(("x1", "x2", "x1Scale", "x2Scale"), (a, b, s, t)):
        value.tofile(work / "input" / (name + ".bin"))
    activation = np.maximum((a.astype(np.float32) @ b.astype(np.float32).T) * s[:, None] * t[None, :], 0)
    maximum = activation.max(axis=1)
    scale = np.where(maximum > 0, maximum / np.float32(127), np.float32(1))
    expected = np.clip(np.rint(activation / scale[:, None]), -128, 127).astype(np.int8)
    expected.tofile(work / "output/golden_y.bin")
    scale.tofile(work / "output/golden_yScale.bin")
    env = dict(os.environ, CAMODEL_LOG_PATH=str(logs), STARS_LOG_PATH=str(logs),
               OPENBLAS_NUM_THREADS="1")
    try:
        proc = subprocess.run([str(binary), *map(str, shape)],
                              cwd=work, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        (work / "run.log").write_text(output)
        failure = dict(case_id=case_id, shape=shape, mode=mode, variant=variant,
                       binary_sha256=binary_hash, status="timeout", timeout_seconds=timeout)
        (work / "failure.json").write_text(json.dumps(failure, indent=2))
        print(json.dumps(failure), flush=True)
        raise
    (work / "run.log").write_text(proc.stdout)
    if proc.returncode:
        raise RuntimeError(f"{variant} {shape}: exit {proc.returncode}; see {work}")
    y = np.fromfile(work / "output/y.bin", np.int8).reshape(m, n)
    ys = np.fromfile(work / "output/yScale.bin", np.float32)
    task = (logs / "profile_task_log0.toml").read_text()
    duration = re.search(r"^\s*duration\s*=\s*(\d+)", task, re.M)
    ticks = re.search(r"Total tick: (\d+)", proc.stdout)
    result = dict(case_id=case_id, shape=shape, mode=mode, variant=variant,
                  binary_sha256=binary_hash,
                  mismatches=int(np.count_nonzero(y != expected)),
                  scale_ok=bool(np.allclose(ys, scale, rtol=1e-4, atol=1e-4)),
                  scale_max_diff=float(np.max(np.abs(ys - scale))),
                  task_cycles=int(duration[1]) if duration else None,
                  total_ticks=int(ticks[1]) if ticks else None)
    (work / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--shapes", nargs="+", default=["16x16x32", "4x8x16", "17x33x65", "16x256x256", "16x1025x32"])
    parser.add_argument("--variants", nargs="+", default=["baseline", "optimized"])
    parser.add_argument("--mode", choices=["random", "zero", "zero_rows", "mixed", "signed_scale", "boundary", "extreme_int8", "tiny_scale", "half_boundary"], default="random")
    parser.add_argument("--suite", action="store_true")
    parser.add_argument("--case-ids", nargs="+", type=int)
    parser.add_argument("--resume", action="store_true", help="Reuse completed results; only with unchanged binaries")
    parser.add_argument("--timeout", type=float, default=240, help="Per-process simulator timeout in seconds")
    args = parser.parse_args()
    if args.suite or args.case_ids:
        selected = [c for c in SUITE if not args.case_ids or c["id"] in args.case_ids]
        results = [run_case(tuple(c["shape"]), variant, c["profile"], args.resume, c["id"], args.timeout)
                   for c in selected for variant in args.variants]
    else:
        results = [run_case(tuple(map(int, shape.split("x"))), variant, args.mode, args.resume, timeout=args.timeout)
                   for shape in args.shapes for variant in args.variants]
    if any(r["mismatches"] or not r["scale_ok"] for r in results):
        raise SystemExit(1)
