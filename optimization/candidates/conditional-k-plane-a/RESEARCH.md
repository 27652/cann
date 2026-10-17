# Conditional K-plane A

Derived from the tileM=16 persistent MIX source. K-plane execution is enabled
only when K has 2--4 safe chunks and the ordinary MN tile grid has at least a
2x underfill relative to the available Cube cores. Other shapes use the
original single INT32 plane and Vector path. This is an isolated candidate;
the root kernel and formal evidence are unchanged.

The intent is to retain the K-plane implementation while avoiding its measured
regression on well-filled large-M/N grids.

## Validation and official exploration (2026-10-17)

Main and benchmark compiled with CANN 9.1 / dav-2201. Local strict smoke
stopped at aclInit=500000 before kernel execution; no local device pass is claimed.
Following the user's Fast Track request, submitted frozen dynamic editable payload
(kernel.asc only): `6ad32b0b193e507d8e84c2f8`, official Pass 15/15, valid=true,
exact-submission ranking score **16.60**. This is below the 16.66 best; not promoted.

Sanitized result, score attribution and exact upload manifest are retained in
`official-exploration.json`; source recovery is `submit-project/`. No new entry
was added to `evidence/formal/`. Local broad correctness, INT32 plane merging,
UB and tail behavior remain unverified beyond the official test coverage.
