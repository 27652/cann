# TBest comparison and optimization triage (2026-10-17)

Measured source: official submission `6ad2cb6b193e507d8e02c24b`,
`evidence/formal/fast-track-6ad2cb6b/evidence.json`. TBest source:
`ev/OPTIMIZATION_TARGET_20261017.md`; all 15 numbers equal the corresponding
official result `best_time`. Times are microseconds per supplied metadata.
Row order is the recorded official testcase order, not local regression order.

| Point | Current time | TBest | Current / TBest |
|---:|---:|---:|---:|
| 1 | 44.48 | 2.10 | 21.18 |
| 2 | 12.78 | 1.67 | 7.65 |
| 3 | 35.59 | 2.12 | 16.79 |
| 4 | 164.65 | 7.55 | 21.81 |
| 5 | 179.43 | 8.28 | 21.67 |
| 6 | 224.50 | 12.02 | 18.68 |
| 7 | 1271.26 | 14.68 | 86.60 |
| 8 | 369.78 | 15.80 | 23.40 |
| 9 | 344.38 | 19.27 | 17.87 |
| 10 | 468.87 | 35.63 | 13.16 |
| 11 | 7540.14 | 52.73 | 142.99 |
| 12 | 1155.62 | 64.52 | 17.91 |
| 13 | 1633.99 | 76.73 | 21.30 |
| 14 | 3537.24 | 173.37 | 20.40 |
| 15 | 7382.02 | 340.89 | 21.66 |

## Observations versus hypotheses

- Points 7 and 11 are persistent outliers: historical 11.67 submission had
  1302.31 / 7712.42 us; 11.76 had 1306.21 / 7755.80 us. RNE-mask improved
  these to 1271.26 / 7540.14 us, but did not remove their disproportionate gap.
  These are different official runs, not controlled stage measurements.
- Official shape mapping is unknown. `optimization/test_points.json` is NOT
  the official set. No evidence establishes that point 7 or 11 uses large K,
  small M, a particular N, or an expensive numerical fallback.
- Ratio ranking is diagnostic only. No score formula is inferred from it,
  and improving the largest absolute/relative gap is not proven to maximize score.

## Concrete source-level suspects

1. **Low M parallelism:** host `run_kernel` allocates one core per 128 rows.
   Thus M <= 128 uses one group. This is an implementation fact, not proof
   that matmul is the measured bottleneck. Candidate `row-parallel-16` tests
   16-row aligned ownership below M=1024, K=65536, leaving N whole.
2. **Large-K path expansion:** K >= 65536 converts both int8 inputs to FP32,
   allocates FP32 input workspaces and executes a separately synchronized
   FP32 matmul path. For M >= 1024 this path requests only one core. These
   choices are expensive-looking but no per-stage device timing is available.
   Replacing it with INT8 is NOT a safe drop-in numerical change: it inherits
   historical precision reasons and requires INT32/FP32 boundary testing.
3. **Whole-row Vector ownership:** each paired Vector handles complete rows
   sequentially after matmul, scans risk mask words and uses V_S/S_V events.
   Small M cannot exploit extra cores along N without new row-max reduction
   and ownership protocols. Scalar mask cost is not separated by current timing.
4. **Two-pass activation:** N > VECTOR_TILE_N re-reads matmul results/scales
   for quantization after max reduction. Tile caching or per-tile parallel
   partial maxima may help, but needs UB capacity/lifetime analysis and a
   second-pass synchronization design; simply increasing N core count is unsafe.

## Experiment status and next actions

- `optimization/candidates/row-parallel-16/`: compiled; host partition and
  scale-residency checks passed; no local device validation completed.
- Formal attempt returned HTTP 429, requested 104-second delay, no submission
  ID. Submission flow stopped without automatic retry, per repository rules.
  No new official result or promotion; current best remains 11.80.
- After platform availability is re-established, evaluate the frozen candidate
  once and compare all testcase IDs/times to baseline; changed point timings
  can narrow dispatch hypotheses but cannot reveal shapes by themselves.
- For independent local diagnosis, use serialized matched cases varying M
  around 16/128/1024 and K around 65536, with strict INT32 golden plus separate
  FP32 diagnostic. Do not compete with the existing shared CAModel worker.
