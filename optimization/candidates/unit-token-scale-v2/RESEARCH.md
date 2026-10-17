# Expanded normal-scale mask and 16-row ownership (2026-10-17)

Baseline: submission `6ad2cf40193e507d8e061327`, verified 15/15, score 14.02,
source `23d1d79ea003e5f8818f016a851d289758f93520971c820875a9b96ec0403923`.
Root promoted after an attributable strictly higher official score (see below).

Reference ideas: `reference/03_current_kernel_mapping.md` sparse scalar correction
and finer M ownership; `reference/02_cuda_sources.md` batch dynamic quantization.
These are adapted ideas, not a claim of transplanting verified third-party code.

Changes: skip token multiplication for exactly 1; extend boundary screening to
normal scales in [FLT_MIN, 1e30] (tiny scales use Div); 16-row ownership for all
INT8-path M. Upper limit avoids subnormal reciprocals; larger scales retain exact
scalar correction. Large-K FP32 arithmetic is inherited without repair.

Candidate source SHA256:
`782b57322a4f2ce9c40182e303d77e413b843f58796ad86d2980e6794c8dbc56`.
Release CANN 9.1.0 / dav-2201 candidate build succeeded; binary SHA256:
`2e2f30108fbb99fae924262234aad2ad9c92a4ad50e7bd21869964211e1f5dd1`.
The initial root-project build did NOT compile the candidate (unused CMake
KERNEL_SOURCE); only the subsequent isolated-project build is candidate evidence.

`host_checks.py` passed 24588 partition checks and 1851392 IEEE host mask lanes.
These checks are not device correctness or a strict INT32 device regression.
**未完成本地设备验证。** No CAModel performance claim is made.
Risks: tiny-input FTZ and Div accuracy can invalidate the mask certificate;
small-N packed mask layout is newly exercised; UB lifetime, multicore tails,
tiling rejection/fallback, and synchronization remain device-unverified.
Inherited large-K FP32-vs-INT32 deviations remain documented risks.

Fast Track uses the reviewed CLI directly under AGENTS.md, not the queue's
strict-device-result contract; no fabricated strict result is supplied.
`project-hashes.json` freezes all eight potential editable files; actual dynamic
editable payload is rechecked by CLI before POST. Private responses/build log:
`/tmp/opencode/unit-token-scale-v2-formal/`. Persistent payload/context:
`evidence/formal/fast-track-6ad2d3be/source/`.

Official result: `6ad2d3be193e507d8e0a014d`, valid=true, Pass 15/15,
all precision_ratio=1, matching ranking score 14.37 (rank 224).
The concurrently recorded previous best 14.34 was additionally validated;
eligibility confirmed 14.37 > 14.34. Root promoted; old payload preserved in
`evidence/formal/fast-track-6ad2d309/source/`. Formal v1 evidence validation
uses the eight server-returned context files; `payload_files` separately records
the one truly editable uploaded file. No local device validation completed.
