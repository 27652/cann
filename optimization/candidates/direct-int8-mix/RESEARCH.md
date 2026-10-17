# Direct INT8 MIX, 2026-10-17

Baseline: recoverable official 14.71 submission `6ad2e0a8193e507d8e164f44`,
`evidence/formal/fast-track-6ad2e0a8/source/`.

## Hypothesis and public inspiration

The latest baseline remains 5--27x slower than TBest on most points (official
point 11: 1401.50/52.73 us, 26.58x). Official shape mapping is unknown.
Avoid KFC client/server dispatch by using direct AIC `MatmulImpl` and explicit
producer-to-consumer synchronization in the same MIX launch. This is inspired
by the separation of Cube producer and Vector consumer in:

- https://gitee.com/ascend/cann-ops-adv/blob/58e37b812de0069ab9191717945cd2afd61f653d/src/transformer/grouped_matmul/grouped_matmul_quant_mixcore.h
- https://github.com/Ascend/triton-ascend/blob/main/docs/en/programming_guide/cv_fusion_operator.md
  (read 2026-10-17, mutable main documentation, not a fixed revision).

This candidate does NOT implement asynchronous tile pipelining or N splitting.
It waits for the complete M partition before Vector consumption. It tests the
direct dispatch mechanism, not the public implementations' claimed speedups.

## Implementation and qualification

New direct INT8 AIC MatmulImpl uses existing tiling, complete N, <=65536 K chunks
and atomic accumulation. After synchronous IterateAll and End, PIPE_FIX notifies
event 5; paired AIV waits then runs the unchanged VectorStage. The same event
pattern already exists in the baseline's FP32 path. Host tiling, quantization,
single-element path and allocation lifecycle remain byte-identical.

Independent eight-file main project compiled successfully with CANN 9.1.0,
Ascend910B1/dav-2201 Release. Build: `/tmp/opencode/direct-int8-mix-build/`;
logs `/tmp/opencode/direct-int8-mix-{configure,build}.log`.
Host source/layout checks in `host_checks.py`; result `host-validation.json`.

**未完成本地设备验证**. Fast Track intentionally skips CAModel, full strict
INT32 device regression and matched performance measurements. Risks: direct
MatmulImpl support/version differences (server CANN 9.0 vs local 9.1), event
5 routing/memory ordering, output visibility, atomic modulo semantics, stride
and tails, and inherited mask/FTZ/UB lifetime risks. Compile and host checks do
not prove these device properties. No known deterministic blocker identified;
formal correctness/performance must determine acceptance.

Root and frozen op sources are not replaced before a strictly improved,
submission-bound 15/15 official score. Full frozen project identities are in
`project-hashes.json` and `identity.sha256`.

## CLI attempt

The reviewed CLI was invoked with the complete project identity and dynamic
template preflight. The server reported HTTP 401 (session expired) before
accepting the POST; no submission ID, result, score, or formal evidence exists.
Per the submission protocol, this uncertain/unauthenticated attempt is not
retried blindly. Re-authentication is required before a new POST.

The user subsequently selected `/tmp/opencode/cookie` for the controlled CLI.
Submission `6ad2e531193e507d8e1bb641` completed Pass 15/15, all precision ratios
1, and the same-ID ranking returned score **14.94** (rank 221). Full source and
sanitized evidence: `evidence/formal/fast-track-6ad2e531/`; offline validate and
decide against 14.71 both passed. This candidate was promoted to root with the
old root preserved at `optimization/snapshots/pre-direct-int8-mix-14.71/`.
The improvement is 0.23 official score, not a demonstrated large speedup.
Device risks and lack of local device validation above remain unchanged.
