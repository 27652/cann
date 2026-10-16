#!/usr/bin/env python3
"""Strict host reference for INT32 Matmul semantics; not a device benchmark."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np


def int32_dot(a: np.ndarray, b_nt: np.ndarray, chunk_k: int = 4096) -> np.ndarray:
    """Compute a @ b_nt.T with explicit modulo-2**32 INT32 accumulation."""
    total = np.zeros((a.shape[0], b_nt.shape[0]), dtype=np.int64)
    for begin in range(0, a.shape[1], chunk_k):
        end = min(begin + chunk_k, a.shape[1])
        total += a[:, begin:end].astype(np.int64) @ b_nt[:, begin:end].astype(np.int64).T
    wrapped = ((total + (1 << 31)) % (1 << 32)) - (1 << 31)
    return wrapped.astype(np.int32)


def reference(x1, x2, x1_scale, x2_scale):
    acc = int32_dot(x1, x2)
    activation = np.maximum(acc.astype(np.float32) * x1_scale[:, None] * x2_scale[None, :], 0.0)
    row_max = activation.max(axis=1)
    y_scale = np.where(row_max > 0, row_max / np.float32(127), np.float32(1))
    y = np.clip(np.rint(activation / y_scale[:, None]), -128, 127).astype(np.int8)
    return y, y_scale.astype(np.float32), acc


def make_cases():
    cases = []
    for k in (65536, 131072):
        cases.append((f"large_k_{k}", np.full((1, k), 127, np.int8),
                      np.full((1, k), 127, np.int8), np.ones(1, np.float32), np.ones(1, np.float32)))
    # Exactly 128*128*131072 = 2**31: verify the explicit INT32 wrap at the
    # signed upper boundary rather than relying on NumPy's matmul promotion.
    k = 131072
    cases.append(("int32_signed_boundary", np.full((1, k), -128, np.int8),
                  np.full((1, k), -128, np.int8), np.ones(1, np.float32), np.ones(1, np.float32)))
    k = 131072
    cases.append(("extreme_and_zero_row", np.vstack([np.full((1, k), -128, np.int8), np.zeros((1, k), np.int8)]),
                  np.vstack([np.full((1, k), 127, np.int8), np.full((1, k), -128, np.int8)]),
                  np.ones(2, np.float32), np.ones(2, np.float32)))
    cases.append(("negative_and_underflow_scales", np.array([[1, -1, 1, -1], [0, 0, 0, 0]], np.int8),
                  np.array([[1, -1, 1, -1], [-1, 1, -1, 1]], np.int8),
                  np.array([-1.0, 1e-38], np.float32), np.array([1e-38, -1.0], np.float32)))
    # The last channel fixes row_max=127, so the first channels produce exact
    # half-integer quotients 0.5, 1.5, 2.5, and 3.5.
    cases.append(("half_even", np.ones((1, 4), np.int8),
                  np.array([[1, 0, 0, 0], [3, 0, 0, 0], [5, 0, 0, 0],
                            [7, 0, 0, 0], [127, 0, 0, 0]], np.int8),
                  np.ones(1, np.float32),
                  np.array([0.5, 0.5, 0.5, 0.5, 1.0], np.float32)))
    return cases


def run(output=None):
    summaries = []
    for name, x1, x2, s1, s2 in make_cases():
        name = name.rstrip(',')
        y, ys, acc = reference(x1, x2, s1, s2)
        assert acc.dtype == np.int32 and np.isfinite(ys).all()
        if name == "extreme_and_zero_row":
            assert ys[1] == np.float32(1.0) and np.all(y[1] == 0)
        if name == "half_even":
            assert y.tolist() == [[0, 2, 2, 4, 127]]
        summaries.append({"name": name, "shape": [x1.shape[0], x2.shape[0], x1.shape[1]],
                          "acc_min": int(acc.min()), "acc_max": int(acc.max()),
                          "y_scale": [float(v) for v in ys], "y_values": y.tolist()})
    result = {"reference": "explicit-int64-then-int32-wrap", "cases": summaries}
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"case_count": len(summaries), "cases": [x["name"] for x in summaries]}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    run(args.output)
