# Wide-row tile/CV reduction candidate

2026-10-17 ablation correction: the formal 16.66 baseline already uses the
same Cube producer, tiling and block count. This candidate does not introduce
a new Cube schedule. The text below saying mask eligibility was restored is
also inaccurate: this frozen candidate narrows the mask range and changes
fallback row mapping. Corrected isolated controls and results are documented
in `../wide-row-ablation/RESEARCH.md`; frozen formal sources remain unchanged.

## Intent

This is an isolated large refactor derived from the existing `n-shard-single-launch`
experiment. It keeps the one-kernel-launch contract but changes the execution
shape for `M <= 16, N >= 8192`: AICs distribute a persistent 2-D M/N tile grid,
while AIVs split each row's post-matmul activation scan across the MIX blocks.
Partial row maxima are written to a launch-private workspace. After the partial
publication barrier each shard independently reduces the same partial maxima
and quantizes only its own N interval; shard zero alone writes yScale.

The normal path remains complete-row Vector ownership. INT32 accumulation,
FP32 conversion, ReLU, row scale, exact correction and INT8 output are retained
from the inherited experiment, with mask eligibility restored to the 16.66
baseline range. The candidate is not a root replacement and does not
claim broad correctness or performance.

## Structural change

Compared with tile16 persistent MIX, the candidate changes both Cube ownership
and Vector ownership for the narrow-M/wide-N regime. It uses exactly two
ordered `SyncAll<false>()` phases in that regime:

1. Cube tile production -> Vector activation reads.
2. Partial maxima -> replicated row-max reduction and N-sharded quantization.

Correction to the previous draft: AIC-only barrier calls are needed to match
the AIV calls inside ProcessShardRows. The AIC half now enters one additional
barrier, matching the one partial-max barrier on AIV. Removing all AIC calls
would be a deterministic protocol error; that draft was never device-tested.

## Validation status

Official evaluation completed at 2026-10-17 07:29 UTC: submission
`6ad32394193e507d8e769935`, Pass 15/15, all precision ratios 1; the matching
ranking record reports score **16.19**, rank 213. This is below the verified
16.66 baseline and is not promoted. Recoverable source and sanitized evidence:
`evidence/formal/wide-row-tile-cv-6ad32394/`. Local device smoke remains unrun;
formal testcase success does not prove unrestricted boundary correctness.

Fast Track decision: user requested direct CLI submission. Compilation and
targeted host ownership checks passed; frozen eight-file project is in
`submit-project/`, hash map in `submit-project-hashes.json`. No local device
validation has completed. The numeric, partial-max cache visibility, MIX
barrier liveness and UB lifetime risks listed below remain explicitly unproven.
There is no currently identified deterministic blocker after protocol review.
The unrelated unsubmitted K-plane diagnostic was terminated at the user's
request after TERM did not stop it; its lease is now free. This is not an
official failure or a score result for that experiment.

- The formal submission is recorded above and was not promoted because its
  matching official score is below the historical best.
- Isolated CANN 9.1/dav-2201 release build passed for both the formal-template
  target and the benchmark target. The benchmark links the local simulator
  runtime through its build RPATH.
- `host_checks.py` passed 24 N-partition ownership configurations and source
  barrier/partial-publication invariants. This is not device correctness
  evidence.
- Device smoke has not run yet: the canonical CAModel lease was initially held
  by the unrelated serialized `k-plane-parallel-int8` benchmark. That
  unsubmitted diagnostic was later terminated per user instruction; no model
  was overlapped and the lease is now free.
- Next checks: strict INT32 smoke focused on M=2/3/16 and N=8192/8193,
  including zero rows and N tails, followed by isolated CAModel diagnostics.
- Partial maxima now use queue-backed MTE3 publication rather than scalar GM
  SetValue. N intervals start at multiples of 32 lanes; final quantization is
  genuinely N-sharded rather than returning to complete-row ownership.
- Known risks: scalar GM reads of partial maxima and cache visibility after
  barrier, barrier liveness on MIX,
  activation reload in the final pass, wide-N workspace size, and interaction
  with the large-K FP32 dispatch.
