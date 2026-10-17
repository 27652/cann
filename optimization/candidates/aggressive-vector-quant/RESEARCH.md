# Aggressive vector quantization (isolated worker candidate)

Date: 2026-10-17. Baseline is the recovered 14.34 source
`evidence/formal/fast-track-6ad2d309/source/kernel.asc`, SHA256
`0cc3bc53431a46e63700e71f7a4568ee297c552ec5281a4e57f186ed60cb0e46`.

## Variants

* **A (`bench_a`)** sets `QUANT_VECTOR_ONLY=1` and disables the mask. It keeps
  the vector RNE result without scalar `FastExactQuantPrepared` correction.
  This is deliberately an inexact benchmark ablation and is **not** a strict
  or submit candidate. It is intended only to estimate the upper bound of
  removing scalar correction work.
* **B (`bench_b`)** keeps vector RNE plus the existing `Compares` mask and
  explores scalar UB staging of risky lane indices. It uses only APIs already
  present in the baseline (`Compares`, tensor `GetValue`/`SetValue`, and
  `TBuf`); it does not use or claim `GatherMask`, `Scatter`, ballot, or a
  compression intrinsic. `CompactLowestLane` is a scalar bit scan.

The retained `main.asc` is the eight-file template's fixed 16x16x32 runner,
despite target names `bench_a`/`bench_b`; it does not accept shape arguments.
At N=16 B uses the all-lane exact fallback and does not exercise compaction.
For Coordinator profiling at N>16, compile the existing shape-aware
`optimization/bench.asc` against this frozen kernel with the recorded variant
macros and record that new binary identity. No shape-aware executable was
claimed or run here. Full-vector integer RNE was not implemented: a verified
device arithmetic/mask certificate is still missing, so sparse scalar staging
is the implemented B research branch, not a full-vector exact algorithm.

## Correctness and submission status

B is an **unverified prototype and not Fast Track eligible**. The baseline
documentation does not establish the device reciprocal error bound, the
`Compares` byte mask layout used by the current source, or the lifetime and
aliasing behavior of the added index buffer. Therefore no strict numerical
result is claimed, even if host helper tests pass. A cannot be submitted by
construction because it omits exact correction.

No CAModel was started, no device smoke was run, and no formal CLI or
credential was accessed. Coordinator must schedule any device work serially.

## Static checks and build

The source was copied byte-for-byte before the prototype edit. The build was
run with `source ../../../../env.sh Ascend910B1 && bash ./run.sh`.
CANN 9.1.0 / Ascend910B1 / dav-2201 compiled both targets successfully (only
the existing `cce_global` host-call warnings). `build/bench_a` SHA256 is
`1f325d6ca3e2dc43db592979f560ff3fd40e205a62d80179601d100adbd06048` and
`build/bench_b` SHA256 is
`bb9d45671fb81a3e62f026f7736726d200c96b544428a55b84d7baeea67ad719`.
All source/template hashes and binary hashes are in `hashes.sha256`;
configure/build output is in `configure.log` and `build.log`.

`host_checks.py` completed host-only checks: 264,192 mask words,
4,193,179 staged lanes, 595,422 exact-helper checks, and 27,114 A
counterexamples. The A counterexample is expected evidence that vector-only
is not strict. `host_checks.json` explicitly sets
`device_validation_completed=false` and both variants ineligible.

Risks retained: mask lane layout, reciprocal/FTZ and half-tie behavior,
scalar index cost, UB capacity, and synchronization around V/S events. No
performance conclusion is made without a paired Coordinator experiment.

Initial build invocations failed before compilation because of a wrong env
relative path and missing executable permission; both were corrected. Initial
host helper extraction accidentally retained an AscendC include; its failure
log is preserved as `host_checks.initial-failure.log`, followed by a corrected
successful run. Python syntax checks passed. No numerical acceptance criterion
or golden was weakened. The original seven supporting template files remain
historical (FP32 golden); they were not used as strict validation.
