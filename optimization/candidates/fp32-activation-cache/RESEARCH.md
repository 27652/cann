# Candidate A: FP32 activation cache

This isolated candidate is derived from the verified 16.66 root source. It
keeps the Cube producer, tile ownership, row ownership, barriers, reduction,
quantization and one-launch contract unchanged. For `N > VECTOR_TILE_N`, the
first Vector pass writes the already converted/scaled/ReLU FP32 activation
tile to launch-private GM. The quantization pass reads that cache instead of
reloading INT32, casting, scaling and applying ReLU again.

For `N <= VECTOR_TILE_N`, the existing UB reuse path remains unchanged and no
activation cache workspace is allocated. The cache is an optimization only;
the output semantics still use the original INT32-to-FP32 conversion and
quantization code.

Validation: CANN 9.1/dav-2201 benchmark and formal-template builds passed. The
frozen eight-file payload was submitted after rechecking the interrupted 132s
429 wait against its unchanged manifest and hashes. Submission
`6ad32d3e193e507d8e88c539` passed 15/15 with all precision ratios 1; same-ID
ranking score **16.63**, rank 212. Recoverable validated evidence and exact
server source are in `evidence/formal/fp32-activation-cache-6ad32d3e/`.
Official score remains below the verified 16.66 baseline; do not promote.

Strict local CAModel smoke was not completed; the previous shared harness
failed at `aclInit(nullptr): 500000`, which is an environment failure before
kernel execution. No official score. Known risks are MTE3 publication ordering,
FP32 cache workspace size, tail padding, and cache lifetime before the second
pass. Root kernel and frozen formal evidence remain unchanged.
