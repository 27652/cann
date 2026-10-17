# Independent structural probes, 2026-10-17

Verified parent: official 16.66 / 15 of 15 submission
`6ad31941193e507d8e654e7b`, kernel SHA256
`cdde82ec40d96b91624cb80dafc3cf5fc547a2168e3a294c5bc40de4044501ae`.
Root and pre-existing candidates are not changed.

## dual-aiv

Change only the active persistent kernel from MIX 1:1 to MIX 1:2 and partition
complete rows over both paired vector sub-blocks. Cube tiles, arithmetic,
workspace and one global handoff remain unchanged. Hypothesis: the existing
one-AIV-per-AIC structure leaves half of the physical Vector cores unused.
This is not a measured bottleneck. Important risks: block/subblock semantics,
SyncAll 1:2 ordering, vector task coverage and UB allocated per sub-block.

## ub-resident-8192

Change Vector buffer lifetimes, independent of dual-aiv. During row max,
divisorBuffer serves as ReduceMax scratch. During quantization, the future half
cast buffer serves as FP32 denominator/mask scratch; a vector barrier precedes
its final half overwrite. This removes the separate reduction buffer while
enlarging half storage, reducing per-lane live allocation from 25 to 23 bytes.
8192 columns use 188416 bytes plus 1088 bytes scale/reduction/mask storage,
within the target's 192 KiB UB budget. Rows up to 8192 can avoid the second
GM-load/cast/scale/ReLU pass. No algebraic scale reassociation is introduced.
Risks: alias lifetime/barrier correctness, ReduceMax scratch requirements,
larger per-core allocation and padded mask lanes. No local device validation
or score exists at creation. Neither candidate is combined or promoted.

Other sessions were already posting formal submissions at discovery time;
do not start a competing POST flow. Compile/host checks can proceed separately.

## Results

- Both variants compile under CANN 9.1/dav-2201. Static ownership checks cover
  288 configurations and all frozen project hashes verify.
- `dual-aiv` was rejected by strict CAModel smoke at `17x513x65`: 2023 INT8
  mismatches and yScale max absolute error 8.2241907. The run is preserved in
  `dual-aiv/results/strict-smoke-v1/`; no formal submission was made. The
  likely fault class is MIX 1:2 sub-block mapping or synchronization, but the
  exact cause is unproven. Do not combine this code with another candidate.
- `ub-resident-8192` passed strict INT32 smoke at `2x4097x33`, `2x8192x33`,
  and `2x8201x33`, with zero INT8 mismatches and exact yScale. This is targeted
  evidence only, not broad correctness or performance proof. Its candidate
  source SHA256 is `155afee07a5d0c77fae096b4cafeefd0bc1d03b2018f625e95cc22c08f31f58d`.
  Formal submission is intentionally serialized behind already active POSTs.

## Official feedback and decision

Once the existing POST processes exited, submitted only UB residency, through
the reviewed CLI with dynamic template and frozen project hash verification.
The server explicitly rejected the first POST with HTTP 429 / 75 seconds;
one permitted retry accepted submission `6ad3365d193e507d8e999c3a`.
Official Pass 15/15, all precision_ratio=1, matched ranking score **16.79**,
queried at `2026-10-17T08:49:16Z`. Actual uploaded editable payload: kernel.asc
only. Complete source context, dynamic manifest and allowlisted result:
`evidence/formal/ub-resident-8192-6ad3365d/`; independent validate passed.

Concurrent research produced a higher verified FIFO score **16.89**,
submission `6ad335a8193e507d8e985b8b`; its bundle validate passed. UB's decide
against FIFO rejected promotion because the score does not strictly improve.
Root changed concurrently to FIFO and was not overwritten. No promotion commit
was created for this experiment. Residual alias/UB/FTZ/rounding/tail risks remain.
This official gain versus 16.66 is small, not the desired large breakthrough.

Old baseline bundle was concurrently given an unexpected
`source/kernel.asc.backup-before-fifo-promotion`, causing its source-set
validation to fail. Do not delete another session's backup; candidate evidence
was validated independently and compared against the clean FIFO bundle.
