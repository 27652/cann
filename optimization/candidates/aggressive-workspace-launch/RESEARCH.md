# Aggressive workspace/launch candidate

Date: 2026-10-17

## Baseline and hypothesis

Baseline is the recoverable 14.37 bundle in
`evidence/formal/fast-track-6ad2d3be/source/` (kernel SHA256
`782b57322a4f2ce9c40182e303d77e413b843f58796ad86d2980e6794c8dbc56`).
The ordinary `run_kernel` allocates a GM workspace, launches the kernel,
waits on the supplied stream, and frees that workspace on every call. The
wait is required: freeing it before completion is a use-after-free, and a
static buffer would be unsafe across streams, devices, or overlapping calls.

## Candidate

For the exact shape `M=N=K=1` only, dispatch launches an AIV-only kernel with
no workspace argument or allocation. It computes the one INT32 product,
casts to FP32, applies both scales in order, applies ReLU, computes
`rowMax/127` (or `1.0` for a zero row), and uses the existing exact integer
RNE/clamp helper. Temporary storage is launch-private UB; no static state is
shared and no buffer is freed while a device operation can still use it.
All other shapes use the unchanged baseline workspace path. Dispatch depends
only on the validated input shape and does not guess any formal testcase.

## Validation

`host_checks.py` performs strict INT32/FP32 reference comparisons for the
single-element path, including negative products, zero rows, scale ordering,
half-even boundaries, and a randomized shape-dispatch guard. It does not
prove device instruction behavior. No CAModel was started and no formal
submission was made.

Build status: attempted isolated CMake build with `-j2`; blocked because this
environment has no `ASCEND_HOME_PATH`/ASC package. No `run.sh` was executed.

## Risk and Fast Track recommendation

**Not Fast Track eligible.** The implementation is logically isolated and
avoids the identified workspace lifetime hazard, but the AIV-only launch and
AscendC API usage have not compiled or run on a CANN environment. In
particular, `KERNEL_TYPE_AIV_ONLY`, scalar GM reads, and the small UB cast
sequence require toolchain/device confirmation. Submit only after an isolated
CANN `-j2` build and targeted host/device correctness check succeed.
