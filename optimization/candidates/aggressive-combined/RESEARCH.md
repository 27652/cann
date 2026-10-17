# Combined all-K + row-job + single-element candidate

## Identity

- Built from the recoverable 14.66 source `evidence/formal/fast-track-6ad2dbba/source/kernel.asc`.
- `kernel.asc` SHA256: `e763bfe2fe3682de621febc73b7889539f6a1d686188eb8a27bb619755ac81ea`.
- Compiled binary SHA256: `834aaa1b0eee50ac0c2a326efecde91a9c861ec8505e9afd31a244a27ee2f068`.
- Reproduction script: `assemble.py`; build log: `BUILD_COMPILE.log`.

## Merged changes

This candidate retains the official 14.66 all-K INT8 threshold (`0xffffffffU`),
then imports only the row-job producer/consumer scheduling structure from the
tile candidate and the `(M,N,K)==(1,1,1)` no-workspace launch path from the
workspace candidate. The arithmetic/quantization body and all-K tiling policy
were not replaced by the older candidate sources. Vector A's known incorrect
approximation was not included. N-split was not included.

## Validation and status

- CANN 9.1.0 / `dav-2201` compilation passed in the isolated candidate build.
- Static checks passed for all-K threshold, producer-before-consumer ordering,
  single-element dispatch/helper presence, and payload identity.
- No local device smoke, CAModel run, or strict INT32 device result was run.
- Host-only Fast Track enrollment succeeded as job
  `1792204288134-6b3e22a0f2` in `/tmp/opencode/aggressive-coordinator-20261017/`.
- Formal submission `6ad2dff3193e507d8e1596b6` passed 15/15 with every
  precision_ratio equal to 1. The default team-name ranking query (including
  its space) exactly matched this submission: official score **14.64**, rank
  220. The original no-space query returned no rows.
- Complete eight-file evidence bundle: `evidence/formal/fast-track-6ad2dff3/`.
  Offline validation passed. Promotion decision rejected because 14.64 does
   not strictly improve the verified 14.66 baseline. Root was not replaced
   for this 14.64 submission.
- Subsequent submission `6ad2e0a8193e507d8e164f44` of the same source passed
   15/15 and obtained score **14.71**; that separate result was promoted in
   commit `5125319`. Recovery: `evidence/formal/fast-track-6ad2e0a8/`.
   The 14.64 evidence remains an independent historical result.

Known risks remain: row-job Matmul completion/consumer synchronization, large-K
stride and atomic modulo behavior, FTZ/mask/UB boundaries, and the unverified
single-element device path.
