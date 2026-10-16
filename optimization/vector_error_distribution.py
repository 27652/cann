#!/usr/bin/env python3
"""Measure IEEE vector reciprocal/multiply RNE errors against the exact helper.

This is a host diagnostic, not a proof of device instruction accuracy.  It
reports the minimum distance to a half-integer among mismatches and the bound
needed for a proposed reciprocal relative-error budget.
"""
import argparse
import numpy as np


def exact_rne(q):
    return np.clip(np.rint(q), 0, 127).astype(np.int32)


def run(count, seed, reciprocal_rel):
    rng = np.random.default_rng(seed)
    # Positive normal FP32 numerator/denominator, including q near thresholds.
    a = np.exp2(rng.uniform(-126, 7, count)).astype(np.float32)
    b = np.exp2(rng.uniform(-126, 7, count)).astype(np.float32)
    q = (a.astype(np.float64) / b.astype(np.float64))
    keep = (q >= 0) & (q <= 128) & np.isfinite(q)
    a, b, q = a[keep], b[keep], q[keep]
    # Worst-case signed reciprocal perturbation, then FP32 multiply.
    inv = (1.0 / b.astype(np.float64)) * (1.0 + reciprocal_rel)
    approx = (a * inv).astype(np.float32).astype(np.float64)
    ref = exact_rne(q)
    got = exact_rne(approx)
    distance = np.abs(q - (np.floor(q) + 0.5))
    mismatch = got != ref
    bound = (2.0 ** -24 + reciprocal_rel + 2.0 ** -24 * reciprocal_rel) * q
    print(f"samples={q.size} mismatches={mismatch.sum()} rate={mismatch.mean():.3e}")
    if mismatch.any():
        print(f"mismatch_min_half_distance={distance[mismatch].min():.9e}")
        print(f"mismatch_max_abs_error={np.abs(approx-q)[mismatch].max():.9e}")
    print(f"max_bound={bound.max():.9e} (rho={reciprocal_rel:.9e})")
    print(f"bound_covers_all={bool(np.all(np.abs(approx-q) <= bound + 2**-149))}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=2_000_000)
    p.add_argument("--seed", type=int, default=20261016)
    p.add_argument("--rho", type=float, default=2**-14,
                   help="assumed reciprocal relative error budget")
    args = p.parse_args()
    run(args.count, args.seed, args.rho)
