# Aggressive INT8 all-K candidate

## Identity

- Candidate directory: `optimization/candidates/aggressive-int8-all-k/`
- Baseline: `evidence/formal/fast-track-6ad2d3be/source/` (latest recoverable 14.37 payload), kernel SHA256 before edit: `782b57322a4f2ce9c40182e303d77e413b843f58796ad86d2980e6794c8dbc56`.
- Earlier 14.34 bundle `evidence/formal/fast-track-6ad2d309/source/` was independently checked at SHA256 `0cc3bc53431a46e63700e71f7a4568ee297c552ec5281a4e57f186ed60cb0e46`; it was not used as the copied source after the Coordinator update.
- Candidate kernel SHA256: see `host-checks.log` and `binary.sha256` for the executable hash.
- Complete eight-file project was copied from the 14.37 bundle: `CMakeLists.txt`, `data_utils.h`, `kernel.asc`, `main.asc`, `run.sh`, and the three `scripts/*.py` files. No credential or formal CLI was read or invoked.

## Hypothesis and change

The 14.37 baseline still dispatches `K >= 65536` to a separate FP32 conversion/Cube path. Its INT8 Cube chunk loop is therefore unreachable for those shapes. This candidate changes only `FP32_MATMUL_K_THRESHOLD` to `0xffffffffU`; it retains the baseline INT8 Cube implementation and its `SAFE_ACCUM_K=65536` loop. Consequently every supported K is selected for INT8 tiling. K <= 65536 uses one direct INT32 Cube matmul; K > 65536 uses <=65536 K chunks and accumulates later chunks with the existing `IterateAll<true>(..., atomicAdd=1)` path.

This deliberately does not reuse the concurrent `int8-all-k-safe`, `int8-all-k-128k`, or modified `int8-k-split-no-atomic` directories. Read-only review found the safe candidate's two relevant edits (threshold and K=65536 direct-path condition), while the no-atomic candidate allocates per-chunk workspace and does not pass the atomic flag; neither was copied.

## Build

Built in the isolated candidate directory after `source ../env.sh Ascend910B1`, with CANN 9.1.0, Ascend910B1, `dav-2201`, and `cmake --build ... -- -j2`. Build return code was 0. Full compiler/linker output is in `build.log`; warnings are the existing host parser `cce_global` warnings from `main.asc`.

`run.sh` was not run. CAModel was not started. No device smoke or strict INT32 device result was produced.

## Targeted host checks

`host-checks.log` verifies the all-K threshold, `SetOrgShape`, chunk `SetTail`, atomic partial path, and guarded `GetMDLConfig(true)`. It enumerates chunk partitions at K boundaries 65536/65537/131072 and beyond, checks every chunk is <=65536 and covers K exactly, verifies the maximum positive chunk sum `65536*127*127 < 2^31`, and checks a signed modulo-2^32 partial-sum model.

These are source/host arithmetic checks only. They are not strict INT32 device correctness and do not create a Fast Track strict-result artifact.

## Risks and unresolved questions

1. `SetTail(jobRows, N, chunkK)` must make the Matmul API consume the shifted GM pointers with the intended K stride. `SetOrgShape` retains full K, while each chunk supplies a reduced tail; this compiled but is not a device semantic proof.
2. K=65536 crosses the hardware 16-bit stride boundary. `GetMDLConfig(true)` is retained to request the guarded/cyclic GM-to-L1 move path. Device behavior for A/B row strides >=65536 remains unverified.
3. For K>65536, later chunks use GM atomic add. Hardware atomic addition must have the intended signed INT32 modulo-2^32 behavior, and the first-chunk initialization must complete before the next chunk's atomic update. The loop is synchronous per client, but cross-core and Matmul internal ordering are not locally proven.
4. Workspace remains `M*N*sizeof(int32)` for the INT8 path. This is intentional for in-place partial accumulation, but any tiling API use of hidden/system workspace or atomic protocol is unverified.
5. Full-K INT8 accumulation follows the题面 INT32 semantic, while historical local scripts/goldens may use FP32 matmul for some cases. No claim is made about formal precision or score.
6. Tail M/N ownership, `SetSingleShape`, padding, N tails, negative/tiny scales, FTZ, and quantization edge behavior are inherited from the 14.37 baseline and were not device-tested here.

## Fast Track recommendation

Not eligible for the Coordinator's normal strict-result enrollment because no strict INT32 device `result.json` was generated. It may be considered for the user's direct Fast Track policy only as an explicitly unverified candidate after Coordinator review, with the above risks preserved. This worker did not enqueue or submit it.
