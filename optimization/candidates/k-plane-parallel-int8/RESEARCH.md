# K-plane parallel INT8 candidate (E)

## Hypothesis

The promoted tile16 MIX kernel already uses INT8 Cube chunks for large K, but
serially accumulates later chunks into one GM plane with `atomicAdd`. This
candidate gives every `<=65536` K chunk an independent INT32 GM plane and
schedules `(M,N,K-chunk)` jobs over the Cube blocks. The Vector stage then
loads and sums the planes in INT32 before FP32 scaling and quantization.

## Validation

- Built with CANN 9.1.0 / Ascend910B1 / dav-2201.
- Strict simulator cases passed with zero INT8 mismatches and exact yScale:
  `2x33x65537`, `2x17x131073`.
- The larger `17x257x131073` isolated simulator run was not completed within
  the available validation window; this is not treated as a pass or failure.
- Host strict golden regression remains the repository reference.

## Status and risks

The candidate was formally submitted as `6ad32449193e507d8e77ed6a` and
received Pass 15/15 with official ranking score 16.32. It was not promoted:
the verified tile16 persistent best is 16.66. The independent planes multiply
workspace by the K-chunk count and make the Vector stage read every plane;
the official per-testcase times were 0.11% faster on point 2 but 3.28--7.15%
slower on points 3--15 versus the 16.66 evidence bundle. Large M/N cases
therefore dominate the regression. The recoverable formal bundle is
`evidence/formal/k-plane-parallel-int8-6ad32449/`.
