# Aggressive N-split / 2D tiling prototype

Date: 2026-10-17

## Baseline and hypothesis

Baseline is the recoverable 14.34 formal project at
`evidence/formal/fast-track-6ad2d309/source/`; its `kernel.asc` is the source
of this candidate. The workspace already contains a separate concurrent
untracked `optimization/upper_bound/` experiment; it was left untouched.

Candidate `kernel.asc` SHA256:
`e7fcffc8c8d34f404ab30b0fb3d1b1c069d8299df7893e05f3107d9d08ae8a31`
(identical to the baseline source except for the documented host-side
prototype additions).

The current kernel assigns each Cube/Vector group complete N rows. For small M,
large N and K below 65536, splitting columns might expose additional Cube
parallelism. A direct enablement is not safe in the existing fused launch:
each N shard would see only a partial activation row, so its row maximum is
not the final `rowMax`; independently produced `yScale` values would race;
quantization must wait until all partial maxima have been reduced. The kernel
has no proven global grid barrier or second launch between these phases.

## Candidate contents and implementation

This directory contains the complete eight-file project copied from the
baseline bundle. `kernel.asc` adds a host-side N-shard partition planner and a
standalone 2D Matmul tiling prototype with shape bounds `M<=32`, `N>=4096`,
`K<65536`, target shard width 2048, and a maximum shard count bounded by
available cores. Each planned shard has a contiguous N range. The tiling
prototype expects a packed `[M, shard_width]` result and one Cube core; callers
would also have to offset the source B pointer by `n_start*K` and place output
in shard-private storage.

Crucially, the prototype helper is not wired into `run_kernel` or the launched
kernel. Runtime continues to use the baseline complete-N ownership and its
existing single-writer row-scale behavior. This isolates the idea while
avoiding an incorrect partial-max implementation. The helper is not a
submittable optimization.

## Ownership / protocol analysis

The host check covers planner ranges for M 1..32, representative N values
around alignment and shard boundaries through 65535, K in the bounded dispatch
region, and core counts 2..64. It checks contiguous, nonempty ranges with no
overlap and exact N coverage. This is only a host mirror of the geometry; it
does not invoke the CANN tiling API or establish runtime ownership.

A correct eventual implementation must use two explicit phases:

1. Cube shards compute partial matmul/activation values and shard maxima; a
   single designated reducer combines maxima in canonical N order and writes
   exactly one `yScale` per row.
2. After a device-wide ordering point (most simply a second kernel launch),
   shards reload/recompute their activations and quantize using that one final
   scale. Output shards must have disjoint byte ranges, including N tails.

The current one-launch MIX kernel offers no demonstrated grid-wide barrier.
Separate `AIV` groups may not assume another group's GM writes are visible
before quantization. Reusing `yScale` as a spin/barrier flag is also unsafe
without documented memory ordering, forward progress, and occupancy proofs.
Therefore no protocol implementation or correctness claim is made.

## Validation status

- Baseline: recoverable 14.34 bundle; working root and formal best were not
  modified.
- Host ownership script: run with
  `python3 optimization/candidates/aggressive-n-split/host_ownership.py`.
- CANN compile: pending; this environment's `ASCEND_HOME_PATH` was not set
  when inspected. Isolated CMake configuration was attempted with
  `-DNPU_ARCH=dav-2201 -j2` and failed before source compilation because CMake
  could not find package `ASC` (`ASC_DIR`/`CMAKE_PREFIX_PATH` unavailable).
  Exact output is in `build.log`; `run.sh` was not executed.
- No local device test, no CAModel, no strict INT32 JSON, and no formal CLI call.
- Eight-file project SHA256 manifest: `payload.sha256`.
- Binary hash: `binary.sha256` explicitly records that no executable was
  produced. No source-level compile claim is made.

## Fast Track decision and risks

**Not Fast Track eligible.** The N-split is only a tiling prototype and is not
runtime-enabled. Connecting it without inter-shard maximum reduction,
single-writer yScale, launch ordering, correct B/output offsets, and a
second-phase quantization pass would deterministically produce incorrect
results or races. Even after protocol work, residual risks include device
tiling behavior, shard tail alignment, INT32 accumulator behavior, float
scale/activation rounding, UB lifetime, and large-K fallback coverage.

Next step: prototype a two-kernel path with shard partials plus per-row final
scales, add an independently testable workspace/layout contract, and only then
compile and run strict INT32 device cases. The baseline path should remain the
dispatch fallback until those phases are proven.
