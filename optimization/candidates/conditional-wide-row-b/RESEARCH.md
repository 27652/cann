# Conditional wide-row B

Derived from the baseline-compatible vector-only wide-row ablation. It keeps
the baseline Cube producer and mask eligibility, and enables N-sharded
partial-max/quantization only for M <= 16, N >= 16384, and more than one active
shard (at most 8, with at least about 2048 columns per shard). All other shapes
retain complete-row Vector ownership. This isolates
the B architecture from the earlier Cube/mask/row-partition confounders.

The candidate is isolated; the root kernel, frozen op files, and formal
evidence are unchanged. Partial maxima use separate aligned 32-byte slots;
publication and reload both use DMA. Idle AIVs still join the collective barrier.

## Validation and official exploration (2026-10-17)

Main and benchmark compiled with CANN 9.1 / dav-2201; 24 host ownership/protocol
configurations passed. Local strict smoke stopped at aclInit=500000 before kernel
execution; no local device pass is claimed. Following the user's Fast Track
request, submitted frozen dynamic editable payload (kernel.asc only):
`6ad32bc0193e507d8e862049`, official Pass 15/15, valid=true, exact-submission
ranking score **16.44**. Below the 16.66 best; not promoted. The CLI retried once
after an explicit 429 response and the server-specified 21-second delay.

Sanitized result, score attribution and exact upload manifest are retained in
`official-exploration.json`; source recovery is `submit-project/`. No new entry
was added to `evidence/formal/`. Local broad correctness, partial-max visibility,
collective synchronization, UB and tail behavior remain unverified beyond the
official test coverage. Official testcase shapes and dispatch activation are unknown.
