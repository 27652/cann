# Independent ownership repair / L0C lifecycle probes

2026-10-17. At creation, best was independent FIFO 16.89; probes were isolated.
Both use the older 16.66 architecture so results remain attributable and do not
mix an unproven dual-AIV or external-chunk protocol into FIFO.

## dual-aiv-fixed

Installed dav_c220/kernel_operator_sys_var_impl.h:55-70 implements AIV
GetBlockIdx as raw block * task ratio + sub-block. The old dual-aiv prototype
multiplied this logical index again. Repair only that expression. Keep 1:2
launch, complete row ownership, Cube tiling and exact numerical logic unchanged.
Host ownership checks must model actual logical AIV IDs, not paired AIC IDs.
Risks: service CANN version, hardware fusion handoff, idle participants, tails.

## l0c-chunk64-probe (diagnostic only, NOT a formal candidate)

Force external K chunks of 64 to exercise Iterate(false), SetSingleShape /
SetTensor resets, Iterate(true), final GetTensorC and repeated tile lifecycle on
small strict-device tests. Keep the one-base-tile guard. This diagnostic must
not be submitted for performance. MDL scheduler_mdl.h:52-62 allocates CO1 only
for !enPartialSum and calls ReduceK(enPartialSum); trace the common MDL reset,
ReduceK and GetResult paths before interpreting success as API support.

## Actual feedback

dual-aiv-fixed passed three strict INT32 CAModel cases, then official 15/15
with same-ID score 19.45. Promoted in commit 31a0781; formal evidence and exact
source are in evidence/formal/dual-aiv-fixed-6ad33b78/. See its RESEARCH.md.

l0c-chunk64-probe compiled and passed strict INT32 CAModel 2x33x129 and
17x257x193, zero INT8 mismatch, exact yScale (rtol=atol=1e-4). This exercises
the small-K external chunk path but does not prove original large-K behavior,
API portability or performance benefit. Not formally submitted or promoted.
No original-large-K device test was run. No combinations submitted.

Installed MDL trace: scheduler_mdl_base.h:97 resets only isFirstIter_, while
MoveOnFirstIterate resets M/N/K iterators. scheduler_mdl.h:52-62 allocates
CubeOutBuffer only for !enPartialSum. scheduler_mdl_common.h:85-95 dispatches
K-full/split reduction; :152-157 and :181-191 pass !enPartialSum as initial-C
control; GetResultImpl :335-365 enqueues/dequeues CO1, copies to GM, then frees
it. These installed-header observations plus small probes support further
testing, not an unconditional claim for every selected policy/configuration.
