# Independent architecture trials (2026-10-17)

Three independent prototypes, not a combined submission. Baseline is the
recoverable official 16.66 kernel (`tile16-persistent-6ad31941`, SHA256
`cdde82ec40d96b91624cb80dafc3cf5fc547a2168e3a294c5bc40de4044501ae`).
Root and other researchers' candidates must remain unchanged.

1. `local-k`: one C-tile owner, Iterate(enPartialSum) retaining L0C across
   external <=65536 K chunks, one GetTensorC at the end. Initially guarded to
   K < 131072 to avoid introducing unproven L0C overflow semantics. Larger K
   retains baseline atomic/modulo behavior. Tile must fit a single baseM/baseN
   block; otherwise baseline fallback. L0C lifetime across SetTensor/reset is
   unproven until device tests. No performance claim.
2. `scale-owner`: derived from isolated conditional-wide-row-b (official
   16.44), not the cache candidate. One owner per row reduces partial maxima
   and broadcasts {outputScale, isZeroRow}; all MIX halves execute three
   barriers in shard mode. Added barrier can outweigh saved duplicate work.
3. `tile-fifo`: bounded two-slot paired AIC/AIV queue, rebased onto tileM=16
   baseline, reusing the historical row-ring event protocol. This validates
   ready/free backpressure, NOT global dynamic work stealing. Installed
   returning scalar atomic APIs are guarded for architecture 3510, not target
   dav-2201; global dynamic allocator remains blocked on a supported primitive.
   No speculative scalar-GM queue or unsupported atomic is submitted.

All three benchmark prototypes compiled under CANN 9.1/dav-2201. No numerical
device test was completed for these prototypes. The first
build failed on harness include/library configuration; corrected configuration
then built all three targets. Source hashes are in `source-hashes.json`.

Important local-k blocker: installed `matmul_impl_base.h` SetTensorA/SetTensorB
reset the Scheduler. Although Iterate(enPartialSum) compiles, its retained CO1
lifetime across these resets is NOT established. Treat local-k as an API probe,
not a qualified formal candidate; no submission before this is resolved.
The <=131071 guard avoids overflow but is not a proof of retained accumulator.

The tile-fifo prototype currently has complete-row-job granularity, not N-tile
consumption: the historical ring cannot publish a row before its last N tile
without changing the Vector epilogue. This narrower paired FIFO experiment must
not be described as the requested global dynamic AIC/AIV task queue.
Each prototype needs targeted correctness/feedback separately before integration.

## Independent official feedback and promotion

- `local-k-safe`: `6ad3338a193e507d8e9444c6`, Pass 15/15, score **16.69**.
  Full internal K-loop for K<131072 avoids external-reset lifetime ambiguity;
  K>=131072 retains baseline safe chunks. Original `local-k` probe not submitted.
- `scale-owner`: `6ad3343f193e507d8e95990c`, Pass 15/15, score **16.60**.
- `tile-fifo`: `6ad335a8193e507d8e985b8b`, Pass 15/15, score **16.89**;
  strictly exceeds previous 16.66 and promoted to root. Exact source SHA256:
  `427a35b31dbc75c3afbb8b1681c68f6c852b8f3b5620ca889c62c56f6083bef4`.

All precision ratios are 1. All three exact-submission ranking/source bundles
were recovered and validated under `evidence/formal/`. No local device smoke
was completed for these revisions. Host models passed 81 shard configurations,
24 FIFO ownership/drain models and six K-boundary models. Returning global
atomic allocator is still unproven on dav-2201. No combination submitted.
Older pending statements above describe the pre-submission stage only.

Pre-promotion root snapshot is `snapshots/kernel-before-fifo.asc` (SHA256
`cdde82ec40d96b91624cb80dafc3cf5fc547a2168e3a294c5bc40de4044501ae`). It is
outside the immutable baseline bundle; both old and new bundles validate.
The revised repository rule permits each independently qualified candidate to
take the Fast Track on its own; that does not permit combining unqualified
changes or reusing one candidate's correctness evidence for another. These
three prototypes have only compile evidence so far.
