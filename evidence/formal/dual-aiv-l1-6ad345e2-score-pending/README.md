# Dual-AIV A/L1 reuse: 15/15, score unconfirmed

Historical snapshot: superseded by `../dual-aiv-l1-6ad345e2/` at
2026-10-17T10:08:02Z: same-ID official score 19.48, rank 195, promoted.
The original pending-state observations below are retained for provenance.

Submission `6ad345e2193e507d8ebb20ec`, directly received using the reviewed
CANNJudge CLI, final observation 2026-10-17T09:55:24Z. Status Pass, valid=true,
15/15, every precision_ratio=1. Contest sealed as confirmed by the user.
Ranking returned no matching record; theory_score=0 is NOT an official score.
This is not a validated scored bundle and cannot authorize promotion.

Parent: verified 19.45 dual-AIV `6ad33b78193e507d8ea310c4`, kernel
`bae4d14b3b7eaa918034a8f0bde94bfa49ce38dc2c992d9e7d7326c50ac9fc95`.
Candidate kernel:
`431750131478b8b569b24d0f86e7fc224187d0ec87d81cf0eb4eac60f3fc249a`.

Change: for K<=4096 divisible by 32 and N>256, stage a 16xK A panel in NZ
format in A1; four adjacent N tiles reuse that panel. Retains dual-AIV and
original fallback. No FIFO or external K-chunk accumulation integration.
Grouping and staging change together; this is not a traffic-only ablation.

## Evidence

- `upload-manifest.json`: dynamic template and exact uploaded bytes/hashes;
  only kernel.asc was editable/uploaded. Eight context files in `source/`
  are recoverable and hashed in `project-hashes.json`.
- `pending-result.json`: sanitized exact-ID server result, all testcase timings.
- `ranking-check.json`: sanitized empty ranking outcome with query time.
- `local-strict/`: four strict INT32 results and fingerprints, zero INT8
  mismatches and exact yScale, rtol=atol=1e-4. CANN 9.1/dav-2201.
- `time-comparison.json`: all 15 testcase IDs, baseline/new time, delta and
  relative change. Baseline observed 2026-10-17T09:10:55Z, candidate 09:55:24Z.
  Retrieval times are existing observations, not new network queries.

Raw response remains protected at
`/tmp/opencode/dual-aiv-l1-stride16-current19-result.json`, not committed.
Candidate build/check tooling: `optimization/candidates/dual-aiv-l1-v4/`.

## Decision

Timing feedback: 9 faster, 6 slower. adc7 9.36 -> 8.02 (-14.32%);
adeb 327.58 -> 308.83 (-5.72%). adc3/adcb regress +8.15%/+10.92%.
Keep the recoverable candidate as a useful independent direction; do not
replace the root or claim official score improvement. Timing units follow
the service field without independent inference. Shapes and repeatability
are unknown; no per-shape causality is inferred. Remaining risks include
other L1 tilings/core counts, tails, small-grid utilization and inherited
FTZ/large-K numerical boundaries. Local coverage is not universal correctness.

Next: paired local baseline/candidate diagnostics on known shapes to isolate
grouping/parallelism effects before a new group-size or dispatch revision.
Do not resubmit this unchanged payload. If same-ID score becomes available,
validate a scored bundle and decide using that score instead.
