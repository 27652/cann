# FIFO + UB8192 integration: official 16.85, not promoted

## Identity and provenance

- Candidate: `optimization/candidates/structural-v3/fifo-ub8192/`.
- Parents: FIFO `6ad335a8193e507d8e985b8b` (16.89) and UB lifetime probe
  `6ad3365d193e507d8e999c3a` (16.79), both independently Pass 15/15.
- Kernel SHA256: `656fdcaa873485cc2a7a6fbed57a64411c979f93f13c466c9d5ca6c2a9ac3580`.
- Actual submission `6ad33c2d193e507d8ea490bc`: server `valid=true`, Pass,
  15/15, all `precision_ratio=1`. Matching ranking score **16.85**, queried
  `2026-10-17T09:14:04Z`.
- `upload-manifest.json` records the dynamic template: only `kernel.asc` was
  editable/uploaded. `source/` is the complete eight-file project recovered
  from the genuine server result and verified against the local frozen hashes.
  The legacy validator's eight-file `files` field is recovery context, not a
  claim that all eight files were uploaded.
- Real raw responses remain protected at `/tmp/opencode/fifo-ub8192-result.json`
  and the associated `.ranking.json`, `.submit.json`, `.manifest.json`.
  Their content hashes are indexed in `evidence.json`. This bundle is the
  durable sanitized evidence; source recovery does not depend on those paths.
- Submission received an explicit HTTP 429 rejection with a 109-second wait;
  the reviewed CLI waited and retried once with the unchanged payload, then
  received the submission ID above. No ambiguous-timeout retry occurred.

## Design and validation actually completed

Integrate the independent 8192-column UB scratch lifetime changes into FIFO,
without changing its row-ring dispatch (`M>=1024 && N<=4096`), mathematics,
quantization correction or event protocol. No official testcase shape mapping
is assumed. The two improvements were separately evaluated before integration.

CANN 9.1/dav-2201 benchmark compilation succeeded. Project hash checks and
288 ownership model configurations passed. Strict INT32 CAModel smoke passed
for `1025x65x33`, `2x4097x33`, `2x8201x33`: zero INT8 mismatches, yScale
maximum absolute/relative differences both zero (`rtol=atol=1e-4`). The first
shape exercises FIFO dispatch and the latter two exercise wide-row boundaries.
This is targeted device coverage, not a full general-input proof or a local
performance measurement. Simulator runs were serial.

## Decision and limitations

`python3 evidence/formal_evidence.py validate evidence/formal/fifo-ub8192-6ad33c2d`
passes. `decide` against verified dual-AIV 19.45 correctly refuses promotion.
16.85 is also below FIFO's 16.89. Single official timing samples do not prove
repeatability, but the official score does not qualify this candidate for
promotion. The root was not overwritten by this experiment.

Retain the candidate as a reproducible integration/ablation result. Remaining
risks include UB scratch alias lifetimes, finite/general-scale and RNE limits,
large-K accumulation, subnormal/FTZ behavior and cross-version synchronization.
There is no claim of strict correctness for all legal inputs or of global
optimality. Next larger direction: independently diagnose Cube/Vector demand
before selecting explicit operand reuse or tile-level epilogue fusion.
