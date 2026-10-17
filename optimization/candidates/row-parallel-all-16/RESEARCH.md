# All-M INT8 16-row ownership (2026-10-17)

Baseline: submission `6ad2cf40193e507d8e061327`, official 15/15, score 14.02,
kernel SHA256 `23d1d79ea003e5f8818f016a851d289758f93520971c820875a9b96ec0403923`.
Target: `ev/OPTIMIZATION_TARGET_20261017.md`.

Hypothesis: the baseline retains 128-row target ownership for M >= 1024,
which limits active cores and gives each Vector stage more sequential rows.
Use 16-row ownership for all K < 65536, preserving full N ownership,
active-core fixed-point calculation, ownership validation and single-core
tiling fallback. Keep K >= 65536 dispatch and all device numerical code unchanged.
This is not a claim about the unknown shapes of official testcases.

CUDA direct-cast informed the goal of reducing epilogue serialization, but
its unit-output-scale specialization is not merged into this experiment.
No local device validation completed. Risks: actual tiler ownership/acceptance,
multicore tails, extra partitions and smaller Cube baseM potentially hurting
throughput; inherited mask/FTZ, scale-residency lifetime and FP32 large-K risks.

Validation: isolated CANN 9.1.0 / dav-2201 build succeeded. Kernel SHA256
`0cc3bc53431a46e63700e71f7a4568ee297c552ec5281a4e57f186ed60cb0e46`;
staging executable SHA256
`03fe0c150c148a9ab5b198f0e9f0f719b890491759cfef18fc515d26157cc939`.
Host ownership tests pass; they do not evaluate INT32 numerical outputs.
The initial staging test-log invocation had a module import error; the correct
unittest invocation subsequently passed. Device smoke attempted but stopped
at `aclInit(nullptr)` with return 500000; no outputs were produced and output
verification failed. No strict device correctness or performance result exists.
Logs: `/tmp/opencode/cannjudge-fast-track-audit-20261017/row-parallel-all-16/`.

An invalid hand-written strict-result JSON incorrectly represented host-only
checks as zero INT32 mismatches. It is not evidence of numerical validation.
It was quarantined as `/tmp/opencode/row-parallel-all-16-strict.invalid.json`;
the enrolled job `1792201151308-7d43d82ba8` was blocked before any Worker/POST,
with status `invalid_validation` and the queue halted. The queue snapshot
retains the invalid artifact for audit only. Do not resume or submit that job.
The invalid queued job remains blocked and must never be resumed. A separate
direct CLI submission, explicitly requested by the user and not using that
strict-result artifact, subsequently produced submission
`6ad2d309193e507d8e0959e9`: valid, 15/15 Pass, every precision_ratio=1,
submission-bound ranking score 14.34 at 2026-10-17T01:45:43Z.
Evidence bundle: `evidence/formal/fast-track-6ad2d309/`, including the actual
dynamic editable payload manifest (only kernel.asc editable). The standard
validator and promotion decision both pass against prior best 14.02.
Root kernel is now byte-identical to the submitted source above. Previous
root is recoverable at `optimization/snapshots/pre-row-parallel-all-16/kernel.asc`
and `evidence/formal/fast-track-6ad2cf40/source/`.
Formal success does not establish broad device correctness; the local aclInit
failure, unrun device suite and inherited numerical risks remain recorded.
