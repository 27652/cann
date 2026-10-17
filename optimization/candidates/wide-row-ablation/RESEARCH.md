# Wide-row ablation (2026-10-17)

## Corrected hypothesis

The formal 16.66 baseline and formal 16.19 wide-row candidate have byte-identical
Cube producer bodies, tiling generators, tile size and launch block calculation.
There is no independent Cube scheduling change to ablate. Earlier descriptions
of a new Cube schedule and restored baseline mask eligibility were inaccurate.

Actual differences include Vector N-sharding, an extra symmetric MIX barrier,
partial workspace, narrower boundary-mask eligibility and ceil instead of floor
whole-row partitioning outside sharding.

## Isolated variants

- `baseline`: exact formal 16.66 kernel; also the only meaningful Cube-only
  control because Cube scheduling did not change.
- `vector-only`: formal wide-row candidate with baseline mask eligibility and
  baseline floor whole-row mapping restored. Retains the partial workspace and
  barrier needed for N-sharding. No Cube changes.
- `ancillary-only`: no N-sharding; retains candidate mask eligibility,
  ceil whole-row mapping and scratch sizing/extra launch argument. This is NOT
  labeled Cube-only.

`prepare.py` asserts source identities and Cube/tiling equality before creating
new isolated source files; `source-hashes.json` records their identities. The
formal 16.19 combined candidate remains immutable in its evidence bundle.

## Validation and risks

All three benchmark targets compiled under CANN 9.1/dav-2201. Source identity,
Cube equality and existing 24 ownership configurations passed. Leased serial
strict smoke was attempted, but baseline `2x8192x65` failed at
`aclInit(nullptr): 500000` before kernel execution; no device numerical case
completed. Log: `results/strict-v1/baseline/2x8192x65/run.log`.

Vector-only submitted via Fast Track, after compilation/host checks and with
local device validation explicitly incomplete. Submission
`6ad326cc193e507d8e7c7d4e`: official Pass 15/15, all precision ratios 1;
matching ranking score **16.57**, queried 2026-10-17T07:45:04Z. Below baseline
16.66, no promotion. Recoverable evidence:
`evidence/formal/wide-row-ablation-vector-6ad326cc/`. Actual dynamic editable
payload was kernel.asc only; eight-file server project context is archived.

Ancillary-only CLI initially received an explicit 429 with a 127-second retry
wait, then the outer 120-second command timeout interrupted waiting. A later
user-requested controlled retry succeeded: submission
`6ad32855193e507d8e7f34d3`, official Pass 15/15, all precision ratios 1;
matching ranking score **16.33**, rank 211. Recoverable evidence:
`evidence/formal/wide-row-ablation-ancillary-6ad32855/`.

Vector-only official point 1: 29.34 -> 22.73 us (-22.53%); point 3:
18.66 -> 16.95 us (-9.16%). All other points were slower, including point 2
9.45 -> 9.51 us. Single evaluation per source does not establish repeatability
or prove N-sharding was active for these points. No hidden testcase shape
mapping is available. Aggregate score recovered from 16.19 to 16.57 after
restoring mask eligibility and fallback row mapping, but their individual
effects cannot be separated by the current controls.

Ancillary-only scored 16.33: it improves point 2 against baseline (9.45 ->
9.29 us, -1.69%), while point 1 regresses 32.55% and points 3--15 are slower.
It still mixes mask and row-mapping differences, so those effects are not
individually isolated.

CAModel timings are diagnostic, not official score. Inherited numerical,
partial-max cache visibility, output tail and UB/synchronization risks remain.
