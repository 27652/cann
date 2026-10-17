# Pure Cube 2D producer + independent Vector consumer

Baseline: official 14.94, submission `6ad2e531193e507d8e1bb641`, recoverable
at `evidence/formal/fast-track-6ad2e531/source/`. Root is not edited.

## Hypothesis / architectural change

The baseline assigns complete N to each Cube M partition and couples Vector
row ownership to that partition. Small M can therefore leave Cube cores idle.
Use an AIC-only persistent MxN tile producer followed by an AIV-only complete-row
consumer on the same stream. The stream kernel boundary is the global handoff;
no GM polling, cross-core row-max or reused event protocol is needed. Vector
ownership is independent of Cube tiles. Quantization arithmetic is unchanged.
Additional launch cost and loss of intra-kernel overlap can outweigh parallelism.
No speedup is claimed before an official submission-bound score.

Single-tile Matmul tiling with explicit grid-stride task assignment avoids
assuming that MultiCoreMatmulTiling automatically maps block IDs. The original
M/N/K strides are retained while SetSingleShape supplies actual tile/chunk tails.
K partials remain <=65536 and accumulate serially per output tile into INT32 GM.

## Public references (read 2026-10-17)

- GroupedMatmulQuantMixCore, fixed revision 58e37b812de0069ab9191717945cd2afd61f653d:
  https://gitee.com/ascend/cann-ops-adv/blob/58e37b812de0069ab9191717945cd2afd61f653d/src/transformer/grouped_matmul/grouped_matmul_quant_mixcore.h
  Separate producers/consumers, runtime M/N shape and full-output row stride.
- https://asc.gitcode.com/guide/programming_guide/appendix/faq/matmul_advanced_api_precision.html
  Explicit M/N block offsets; output row stride must be full N, not singleCoreN.
- https://asc.gitcode.com/guide/operator_practice/best_practices/matmul_tuning_cases/matmul_pure_cube.html
  Pure Cube bypasses MIX client/server messaging.
- https://github.com/Ascend/triton-ascend/blob/main/docs/en/programming_guide/cv_fusion_operator.md
  Split kernels/workspace when Vector state crosses Cube tiles; persistent
  physical-core grids rather than many tiny GPU-style dispatches.

These are design inspirations, not copied third-party implementation or proof
of local/server device semantics. Gitcode/main docs are mutable development docs.

## Validation and risks

- CANN 9.1.0 / dav-2201 Release build succeeded, including the local benchmark
  target. One existing CAModel smoke at 16x16x32 matched the strict INT32 host
  reference exactly (`y` mismatches 0, `yScale` max absolute difference 0.0);
  this is archived in `smoke-strict-comparison.json` and is not a full device
  regression.
- Formal submission `6ad2ea60193e507d8e231322` was accepted but ended in
  `Runtime Error` for all 15 cases. The server reported:
  `Profiling rule violated: each iteration must launch exactly 1 kernel.
  Expected 75 launches, got 150.` The two-stage launch is therefore not
  eligible and was not promoted. Reproducible failure evidence is archived at
  `evidence/formal/pure-cube-2d-vector-6ad2ea60/`; the raw response remains
  outside the repository at `/tmp/opencode/pure-cube-2d-vector-result.json`.
- This failure is a launch-protocol violation, not evidence of a numerical
  mismatch or a proven synchronization failure. A future candidate must keep
  exactly one submitted kernel launch per iteration; it must not evade this
  rule by changing the harness or hiding a second launch.

Initially **未完成本地设备验证** beyond the recorded smoke. Risks: AIC-only direct MatmulImpl code generation on
server CANN 9.0 vs local 9.1; SetSingleShape reuse after IterateAll; full N output
stride with N splitting; tails; INT32 atomic wrap/order; workspace lifetime;
inherited FTZ/mask/UB lifetime and scale edge behavior. Compile/host validation
cannot prove device instructions. No fabricated strict device result is used.
