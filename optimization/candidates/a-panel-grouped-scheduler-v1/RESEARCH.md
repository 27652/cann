# A-panel grouped scheduler — independent experiment

Parent: official 16.66 submission `6ad31941193e507d8e654e7b`.

## Hypothesis

The baseline distributes individual M/N tiles cyclically. Consecutive N tiles
using the same A row panel can land on different AICs. This experiment assigns
groups of up to four adjacent N tiles to one AIC, potentially improving cache
locality and reducing repeated A traffic. This is a scheduler architecture
probe, **not a proven L1-resident A-reuse implementation**. No bottleneck or
performance improvement has been measured.

## Isolation

Only tile-to-core ownership/order changes. Cube arithmetic, tiling, safe K
chunks, atomic accumulation, complete GM plane, SyncAll, quantization including
exact correction, workspace and single launch are preserved. If there are
fewer panel groups than launched cores, use baseline scheduling to avoid
obvious core underfill. No FIFO, scale-owner, multi-row or Split-K changes.

## Validation and risks

`prepare.py` refuses to overwrite an existing project and verifies its parent
hash. `host_checks.py` checks exact once-only tile ownership, source invariants
and frozen project hashes. These are host/static checks, not device numerical
validation. Risks: changed tile completion order, tail-group load imbalance,
cache behavior differing from the hypothesis, and inherited numerical/device
boundaries. Local device verification has not been completed.

Build without running destructive root `run.sh`:

```bash
source env.sh Ascend910B1
cmake -S optimization/candidates/a-panel-grouped-scheduler-v1/submit-project \
  -B optimization/candidates/a-panel-grouped-scheduler-v1/build -DCMAKE_BUILD_TYPE=Release
cmake --build optimization/candidates/a-panel-grouped-scheduler-v1/build -j2
```

No official submission or score yet. Formal work must be serialized with any
other active submission flow; do not duplicate the shared architecture trials.

## Current status

`prepare.py` froze the eight-file project with kernel SHA256
`59afc75beb0afbf440615ec547447e75bff82673edaea00d586b7e99b8600679`.
`host_checks.py` passed 420 ownership configurations. The formal-template
project compiled successfully under CANN 9.1/dav-2201 (only inherited
`cce_global` host-side warnings). No CAModel run has been started and no
submission ID or score exists.

## Formal feedback

Fast Track submission `6ad334f3193e507d8e96fa05` completed Pass, 15/15.
The exact-ID ranking returned score **16.58**, below the established 16.66
baseline; not promoted. CLI retried only two explicit HTTP 429 rejections with
server waits of 6 and 180 seconds before acceptance. Frozen payload was
unchanged. Source and sanitized result/manifest/score evidence are retained at
`evidence/formal/a-panel-grouped-6ad334f3/`. This scheduler grouping does not
show an official improvement; do not infer that explicit L1 A reuse would also
fail. No local device verification was completed.
