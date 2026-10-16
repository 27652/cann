# CAModel optimization and regression

## Latest snapshot

The current root candidate is frozen as `op/kernel_v3.asc`. The user's external
15-point evaluation passed all cases with zero output errors, but latency still
lags the reported best times substantially. See `../ev/V3_EVALUATION.md` for the data,
remaining correctness limitations and next-step priorities. Measurements below
describe earlier versions unless explicitly stated otherwise.

## Fixed public test points

`test_points.json` lists 15 newly constructed regression cases (not the user's
15 hidden evaluation cases). The runner uses fixed per-case seeds, preserves
input binaries and NumPy golden binaries, and reports exact INT8 errors, scale
errors, binary hash and CAModel cycles. Newly added cases are not yet validated.

```bash
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py --suite --variants prior optimized
# Run a subset first; cases 12-15 may be expensive in CAModel.
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py --case-ids 1 2 3 4 5 6 --variants prior optimized
```

Target: CANN 9.1.0, Ascend910B1 (`dav-2201`). The original source is preserved
as `baseline/kernel.asc`. Production entry points and build files are unchanged.

## Changes

* Incorporate the supplied `op/kernel.asc` design: 4096-lane UB tiles and
  reciprocal-multiply hints (with Div fallback for tiny scales).
* For `N <= 4096`, reuse the activated FP32 row already resident in UB after
  `FindRowMax`. `ReduceMax` uses separate work/output buffers and does not modify
  this row. This eliminates the second GM read, INT32 conversion, two scaling
  operations and ReLU. Wider rows retain the existing two-pass path.
* Avoid reading approximate quotients and decoding floating-point fields for
  ReLU zeros.
* Only scalar-quantize valid output elements, not alignment padding. Padding
  lanes are independent during narrowing casts and are never copied to GM.
* Hoist output-scale FP32 normalization out of the per-element exact quantizer;
  the denominator is invariant for a row. This preserves the exact integer
  correction while removing repeated denominator decode/normalization work.
* Convert approximate FP32 quotients to floor-INT16 hints with vector `Cast`,
  instead of decoding each quotient's FP32 exponent/mantissa on the scalar
  pipe. Any bad/saturated hint is still repaired by the exact correction.
  The original scalar hint path is retained for `N <= 16`, where vector setup
  costs more than it saves.

The exact positive-element quantizer, rounding rules, dequant multiplication order,
large-K FP32 path, workspace layout and core partition policy are unchanged.
The approximate hint may differ, but its integer certification/correction is
unchanged. `op/kernel.asc` itself is not modified.

## Reproduce

```bash
source ../env.sh Ascend910B1
cmake -S optimization -B optimization/build
cmake --build optimization/build -j4
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py --variants baseline prior optimized
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py --shapes 4x17x32 --mode zero
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py --shapes 4x17x32 --mode mixed
```

Run these serially. Each run has its own input, output, model logs and
`result.json` under `results/<shape>_<mode>/<variant>/`. The driver checks INT8
output with exact equality and scales with `rtol=atol=1e-4`. It also propagates
runtime failures. `--resume` reuses existing results and should only be used
when the binaries have not changed.

Compare `task_cycles` from CAModel `profile_task_log0.toml`, not wall-clock
runtime (which is dominated by simulator startup/logging). `total_ticks` also
includes scheduling/model activity. Results are simulator measurements, not
physical-device latency. Absolute cycle counts depend on input data because
the original exact quantizer uses data-dependent scalar branches.

## Initial measurements (before incorporating `op/kernel.asc`)

The repository's original case (`M=16,N=16,K=32`) passed before and after the
first optimization: task duration 96,298 -> 91,149 cycles, total ticks
97,066 -> 91,630. Both INT8 and FP32 outputs were bit-identical to the supplied
golden. These measurements preceded the additional padding-lane optimization.

Attempting four-row Cube ownership partitions was rejected by the tiling API;
that experiment is **not** part of the final kernel. No approximate division
shortcut or relaxed output tolerance was introduced.

This is a targeted optimization, not a claim of a global optimum. The scalar
exact quantizer remains a significant cost; replacing it safely with vector
integer logic would require additional rounding/subnormal boundary validation.

Host-side helper validation:

```bash
python3 optimization/check_quant.py
```

This checks arbitrary hints against the exact FP32 division reference helper
and checks values around half-integer rounding thresholds. It does not replace
CAModel validation of pipeline synchronization and vector instruction behavior.

## Comparison against supplied prior optimization

Measured vector-hint candidate, before the final `N <= 16` specialization:

| M,N,K | Mode | Prior task cycles | Candidate task cycles | Change |
|---|---|---:|---:|---:|
| 16,16,32 | random | 69,661 | 70,560 | 1.29% slower |
| 17,33,65 | random | 104,042 | 101,470 | 2.47% faster |
| 2,1025,32 | random | 234,914 | 232,342 | 1.09% faster |

All three had zero INT8 mismatches and zero scale difference against NumPy.
These are single measurements, not statistical confidence intervals. The final
small-N specialization is recorded separately in `benchmark_final.log`.
The user's 15-case evaluation shapes are unavailable; these results do not
establish improvement on that evaluation suite. In particular, this incremental
work does not eliminate the scalar correction bottleneck or explain away the
large gap to the user's reported best implementations.

Final small-N-specialized build (all outputs match exactly, including scales):

| M,N,K | Mode | Prior task cycles | Final task cycles | Change |
|---|---|---:|---:|---:|
| 16,16,32 | random | 69,661 | 72,238 | 3.70% slower |
| 4,8,16 | random | 32,753 | 32,767 | 0.04% slower |
| 17,33,65 | random | 104,042 | 100,591 | 3.32% faster |
| 4,17,32 | mixed | 31,879 | 32,750 | 2.73% slower |

The small-N specialization did **not** recover the small-shape regression.
The current root kernel is an experimental candidate, not a consistently
faster replacement for `op/kernel.asc`. Prefer the untouched `op` version if
requiring the previously established 15-case correctness/performance baseline.
