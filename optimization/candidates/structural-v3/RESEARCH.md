# Structural v3: integration and independent corrected dual-AIV

## fifo-ub8192

Parents: official FIFO `6ad335a8193e507d8e985b8b` (16.89), and independent
UB lifetime `6ad3365d193e507d8e999c3a` (16.79), both 15/15 with matched score.
Integrate only the proven-source UB changes into FIFO. Keep FIFO's dispatch
`M>=1024 && N<=4096` unchanged; do not invent a shape mapping from official
testcase indices. Added risk: larger UB with FIFO ring source rebinding,
scratch alias lifetimes, changed runtime/codegen and performance interactions.
The integration does not inherit either parent's score or broad correctness.

Formal feedback: submission `6ad33c2d193e507d8ea490bc` passed 15/15 with
score **16.85**, below FIFO's 16.89 and far below the independently corrected
dual-AIV result. The full recoverable bundle is
`evidence/formal/fifo-ub8192-6ad33c2d/`; `formal_evidence.py validate` passes.
The combination is therefore rejected as a performance integration, although
its exact official result is useful evidence that the scheduling and UB changes do not
compose monotonically. Official per-case times are retained in the evidence
bundle; testcase shape mapping remains unknown.

## dual-aiv-corrected

Independent from FIFO and UB. Parent is original 16.66 persistent 2-D kernel.
Fix first probe's demonstrated incorrect flattening: installed dav_c220
`GetBlockIdxImpl` returns `get_block_idx()*GetTaskRationImpl()+get_subblockid()`
on AIV, so the index already includes the second vector core. Partition rows
using this flat index and `GetBlockNum()*GetTaskRation()`. Cube indexing and
tiles do not change. MIX 1:2 is still a new synchronization/launch configuration
requiring targeted strict device validation before formal submission.

## Larger gap to TBest

Original baseline time/TBest ratios for points 12--15 are approximately
17.18x, 18.63x, 19.19x, 21.86x. Neither a 0.8% score gain nor inferred shape
assignment explains these gaps. TBest may come from different submissions per
testcase; it is not a known single runnable solution. Candidate directions are
to remove Matmul per-tile setup, reuse L1 operands, fuse tile epilogues or reduce
scalar quantization overhead. These are hypotheses, not measured bottlenecks.
Another concurrent workflow submitted its own corrected dual-AIV candidate as
`6ad33b78193e507d8ea310c4`, Pass 15/15, score **19.45**, and promoted it
over FIFO. That candidate has a different source hash from this directory's
`dual-aiv-corrected` (which was not submitted and inherits no official score).
The official candidate's evidence and source recovery are in
`evidence/formal/dual-aiv-fixed-6ad33b78/`. This result is attributable to the
GetBlockIdx flattening correction plus MIX 1:2, not to the rejected FIFO+UB
combination. The remaining risks are large-K accumulation, subnormal/FTZ and
general event semantics; no claim of global optimality is made.
