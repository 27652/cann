# Aggressive tile streaming candidate

Date: 2026-10-17

## Baseline

The candidate is copied from `evidence/formal/fast-track-6ad2d309/source/`, whose
recorded submission is 15/15 and score 14.34. This worker did not read credentials,
modify the root kernel, or invoke the formal CLI.

## Hypothesis and implementation

The baseline launches `CubeStage.Process()` to submit all row jobs, calls `End()`,
and only then starts `VectorStage.Process()`. This candidate keeps complete-N row
jobs but interleaves the synchronous `IterateAll<true>` completion with vector
consumption for that job. `Begin()` registers/configures Matmul once; each
`ProcessRowJob()` submits one bounded row job, and its return is the producer to
consumer handoff. `VectorStage.ProcessRows()` then computes the full row maximum and
quantizes those rows before the next job is submitted. `Finish()` calls Matmul End
only after all jobs.

This is **not** a true asynchronous Cube/Vector pipeline: `IterateAll<true>` is
synchronous and no undocumented event or second Matmul queue was introduced. It is a
restricted two-stage row-job/resident reuse schedule. Whole-row N ownership and the
row-max dependency are preserved. The channel-scale tensor remains resident across
the core's row jobs when enabled.

The FP32 split-core path is intentionally unchanged; no shape/baseN subcandidate was
derived because the available evidence does not isolate tiler/baseN as a bottleneck.

## Validation

- Host CANN 9.1.0 / `dav-2201` isolated configure and `cmake --build ... -j2`: **passed**.
- `python3 host_checks.py`: **passed** 91 host scheduling/ownership combinations and
  source invariants; this is not a numerical or device check.
- Build output: `BUILD_HOST.log`.
- Host source hashes: `project-hashes.txt`.
- No CAModel, device smoke, `run.sh`, strict numerical suite, or formal submission
  was run by this worker.
- Build warnings are the inherited `cce_global` attribute warnings from the local
  host-side invocation; no compiler error occurred.

## Risks / qualification

The new schedule is unproven on device. It assumes repeated synchronous
`IterateAll<true>` calls may be followed by vector GM reads before the final Matmul
`End()`, while retaining the API's internal completion guarantees. This must be
verified against device behavior. Matmul object lifetime, repeated SetTail calls,
K-split atomic accumulation, tail rows, and vector queue reuse remain risks. The
candidate must not be described as complete streaming or strict-correctness proof.
It is eligible for a later Fast Track consideration only after coordinator review
of this synchronization assumption and payload hashes; this worker recommends **do
not submit yet** without targeted device/official validation.
