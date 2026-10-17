# RNE-distance boundary mask (2026-10-17)

Baseline: submission `6ad2c82d193e507d8effe4e2`, score 11.76,
kernel SHA256 `f8c53d3cfaf38bff415c4076d89426d551b04f8a988bff7ea9c989de3cad2163`.

Reference inspiration: `reference/03_current_kernel_mapping.md` (vector
quantization with sparse exact correction) and `reference/02_cuda_sources.md`
(vector RNE and quantization dataflow). This mask transformation is our own
candidate, not code claimed to exist in the cited third-party implementations.

Compute vector RNE once and reuse the rounded result to form
`abs(q - RNE(q)) >= 0.5 - 1/1024`. On the guarded nonnegative quotient range,
this selects the same half-integer neighborhoods as the old FLOOR-based
distance test. It removes a FLOOR cast and an Adds operation; all exact
fallback logic, scale order and matrix multiply paths remain unchanged.
The exact helper accepts arbitrary hints, including RNE rather than FLOOR.

Validation: ASC CANN 9.1.0 / dav-2201 Release build succeeded; host FP32 test
`PYTHONPATH=optimization python3 -m unittest optimization.test_rint_distance_mask -v`
passed 1,006,657 quotient samples, including mask threshold neighbors.
No local device validation was completed. This does not prove device reciprocal,
Cast, Compare or FTZ semantics. Inherited mask error-bound, scale residency
lifetime/synchronization and large-K FP32 numerical risks remain.

Formal submission: `6ad2cb6b193e507d8e02c24b`, Pass 15/15,
all precision_ratio=1, matching ranking score 11.8. Evidence/recovery:
`evidence/formal/fast-track-6ad2cb6b/`. Promoted after strict comparison to 11.76.
Kernel SHA256 `007b6fb9ba6f55d5033f644fcc6cc6c975666ea9dd7d1c4d08bca9e38b674aab`.
Official-project staging binary SHA256
`a9ccf26f1020e47edd61f62c0ff510ebfaa75caf470e8ffbb2872d6d4108505f`.
Staging: `/tmp/opencode/cannjudge-fast-track-audit-20261017/rint-distance-mask/`.
The improvement in one official evaluation is not a repeated-run timing proof.
