# Single-launch MIX 2D Cube + independent row Vector

## Baselines / fix

- Best valid official: `6ad2e531193e507d8e1bb641`, 15/15, score 14.94;
  recoverable at `evidence/formal/fast-track-6ad2e531/source/`.
- Previous two-launch experiment: `6ad2ea60193e507d8e231322`, Runtime Error
  on all 15 cases, explicitly because exactly one launch is required per
  iteration (75 expected, 150 observed). Frozen failure source remains at
  `evidence/formal/pure-cube-2d-vector-6ad2ea60/source/`.
- This isolated candidate replaces its two launches with one MIX 1:1 launch.
  AIC tile task ownership is unchanged. Every AIC/AIV reaches hardware
  `SyncAll<false>()`; only after it completes do AIVs read complete GM rows.
  Row ownership is independent of N-split producer ownership. No GM polling,
  hidden launches, or judge changes are used. The single-element special case
  remains an exclusive one-launch path.
- Quantization arithmetic and the INT8 / <=65536 K-chunk path are retained.
  Legacy unused implementation sections are retained for now; the executed
  dispatch must not be confused with those dead historical branches.

## API evidence (2026-10-17)

`asc/impl/basic_api/dav_c220/kernel_operator_sync_impl.h` in CANN 9.1.0,
`SyncAllImpl<false>`: PIPE_ALL barrier, AIV-in-core handshake, all-AIC
synchronization on PIPE_FIX, then AIC-to-AIV release.

Public API documentation:
https://asc.gitcode.com/api/SIMD-API/basic_api/sync_control/inter_core_sync/SyncAll.html

MIX 1:1 or 1:2 is required, and launch block count must not exceed physical
cores. Host launch cap uses availableCoreNum and platform AIC/AIV counts.
Concurrent multi-stream barriers can deadlock if they oversubscribe physical
resources; that broader environment has not been validated. Documentation
recommends batch scheduling in that scenario. Local compiler/header evidence
does not prove server CANN 9.0 or every hardware/scheduling behavior.

## Validation status / risk

- CANN 9.1.0 / dav-2201 Release compilation succeeded for the formal-template
  main and the separate benchmark. Source SHA256:
  `fade9cbe23d05ffd5b636015b2c59c4e4f9bf63987bd3b4c370624d545ff9f62`.
  Main binary SHA256:
  `25a1992d38a9c1a906883a87b4015c7d47f27b93d841127e666a205d1559ed94`;
  benchmark binary SHA256:
  `60026254dba9daef2c77aee7d316490a369751d2138b01571d8870b61550d00c`.
- `host_checks.py`: 360 ownership combinations and 8 K-chunk configurations
  passed, original VectorStage source unchanged. This does not prove device
  semantics.
- Serial leased CAModel on Ascend910B1 completed three strict INT32 cases:
  17x513x65, 65x257x33 and 2x1025x32, including zero rows/signed scales.
  Every case: INT8 mismatch=0, yScale max absolute and relative differences=0;
  configured tolerance rtol=atol=1e-4. Source/binary/input/reference/environment
  fingerprints and run logs are under `results/single-launch-smoke-v1/`.
- Formal submit invocation started after compilation and host checks, while
  smoke was running. Submission `6ad2ed99193e507d8e278978` then completed:
  valid=true, Pass 15/15, all precision_ratio=1. Official ranking matched this
  exact ID, score **16.07**, rank 213. The full server-context eight files match
  the qualified project; actual editable/uploaded file is only `kernel.asc`.
  `formal_evidence.py recover/validate/decide` passed, relative to 14.94.
  Root was promoted after preserving the complete old root in
  `optimization/snapshots/pre-mix-2d-single-launch-14.94/`.
  Full new evidence/source: `evidence/formal/mix-2d-single-launch-6ad2ed99/`.
  Real raw result and ranking remain under `/tmp/opencode/` with names
  `mix-2d-single-launch-result.json` and `mix-2d-single-launch-ranking.json`.
  This single official measurement improves score by 1.13; case 4 time worsened
  53.52%, while cases 7 and 11 improved 54.17% and 68.62%. No phase-level
  attribution or statistically stable speedup has been measured.

No full strict INT32 device regression is claimed. N-tail strided
output, reused SetSingleShape, K atomic wrap/order, MIX barrier liveness, FTZ,
mask layout, UB lifetime, scale edges and added global synchronization cost
remain risks. The two-launch candidate's smoke is not inherited as this
candidate's validation. Root is now promoted; frozen op files remain untouched.
