# Persistent MIX tile-M=16 candidate

## Hypothesis

The current official 16.07 kernel uses a persistent AIC 2-D tile grid with tileM=64 and tileN=256. Local paired CAModel diagnostics showed the same architecture with tileM=16 reducing task cycles substantially on 64x256x256 and 64x1024x256, while strict INT32 output remained exact. This candidate keeps the single-launch MIX protocol, SyncAll handoff, K chunking, and VectorStage unchanged, and changes only the Cube M tile granularity to 16.

## Public basis

CATLASS documents a small-matmul template that manually assigns task blocks and reduces scalar/scheduler overhead, and a quantized W8A8 template using explicit block scheduling and fused epilogue. References:
- https://catlass.readthedocs.io/en/latest/2_Design/01_kernel_design/04_matmul_summary
- https://github.com/mirror-cann/catlass/blob/b71539e306ca29f82a6f55282e867b8a1f8e0b97/examples/103_dynamic_optimized_quant_matmul_per_token_basic/impl/kernel/per_token_matmul_kernel.h

## Status

Promoted after official submission `6ad31941193e507d8e654e7b`, valid=true,
15/15 Pass, submission-matched ranking score **16.66**, rank 210 (2026-10-17).
Evidence: `evidence/formal/tile16-persistent-6ad31941/`; recover/validate/decide
passed against previous best 16.07. Root matches this exact kernel.
Previous root: `optimization/snapshots/pre-tile16-persistent-16.07/`;
complete previous best: `evidence/formal/mix-2d-single-launch-6ad2ed99/`.
Main project compiled in `build-release`, CAModel benchmark compiled in
`bench-build`, host/source checks passed 360 ownership and 8 K-chunk cases.
Risks include more tile launches, SetSingleShape tail behavior, synchronization
overhead, and tile16 underutilization for large M. Official passage is not a
general boundary correctness proof.

## Completed strict CAModel smoke

CANN 9.1.0, dav-2201 simulator, seed 20261017, strict INT32 golden
`optimization/int32_golden.py`; signed row/channel scales and a zero row.
Shapes below are M×N×K, not official testcase shape assignments.

| Shape | INT8 mismatches | yScale max abs/rel diff | Status |
| --- | ---: | --- | --- |
| 17×513×65 | 0 | 0 / 0 | passed |
| 65×257×33 | 0 | 0 / 0 | passed |
| 2×1025×32 | 0 | 0 / 0 | passed |

Scale acceptance: rtol=atol=1e-4; INT8 exact equality. Fingerprints, input,
golden, output and logs: `results/single-launch-smoke-v1/summary.json` and
per-shape directories. Kernel SHA256:
`cdde82ec40d96b91624cb80dafc3cf5fc547a2168e3a294c5bc40de4044501ae`.
No general large-K/overflow, subnormal/FTZ or concurrent-stream correctness claim.

The earlier paired diagnostics use byte-identical current/tile16 source snapshots
(`optimization/diagnostics/mix-2d-regression/snapshots/`), verified this session.
Follow-up run `tile16-followup-large-v1` failed during baseline `aclInit` with
500000, before any kernel execution. The old diagnostic binary lacks the explicit
CAModel runtime linkage present in the newly built passing smoke binary, but this
does not establish the failure's root cause. A second serial run with an explicit
dav-2201 simulator library path (`tile16-followup-large-sim-v1`) failed at the same
initialization point. Neither run produced kernel correctness/performance data;
no current/tile16 variants ran. Root cause remains unresolved; stop reusing these
old binaries and rebuild explicitly in simulator mode before further comparisons.

## Scope of community-derived work

This is only a scheduling-granularity ablation, not an implementation of online
partial maxima, CV ring buffers, full-load-A or multi-core Split-K. Design and
applicability analysis: `optimization/COMMUNITY_STRUCTURAL_RESEARCH_20261017.md`.
