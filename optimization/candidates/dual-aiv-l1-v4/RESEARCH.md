# Dual-AIV v4: explicit A/L1 reuse

Final archival note (2026-10-17): the same-ID CLI ranking later confirmed
score **19.48**, rank **195**, for `6ad345e2193e507d8ebb20ec`; stride16 was
promoted in commit `b60f59c`. See `evidence/formal/dual-aiv-l1-6ad345e2/`
(repository-relative) and `optimization/RESEARCH_HANDOFF_20261017.md`.
Statements below are chronological observations, not the final pending status.

Parent: official dual-AIV `6ad33b78193e507d8ea310c4`, 15/15, score 19.45,
kernel SHA256 bae4d14b3b7eaa918034a8f0bde94bfa49ce38dc2c992d9e7d7326c50ac9fc95.
Root and other workflows are not edited. Frozen parent remains recoverable.

## Observations, not timing claims

The parent uses one global INT32 M*N plane, a fusion barrier after all Cube
tiles, then complete-row AIV epilogues. Each Cube task resets A/B per 16x256
tile. Wide-N epilogues read/activate INT32 twice. No stage latency attribution
has yet been measured; simulator lifecycle includes waits and is not utilization.

Existing concurrent n-tile-max-pipeline derives from FIFO 16.89, not dual-AIV;
its conservative per-tile ACK serializes Cube/max scan. Do not combine it here.

## Independent breakthrough: a-l1-group4

For K<=4096 divisible by 32 and N>256, explicitly copy a 16xK A panel to A1
in NZ layout, consume four adjacent N tiles from that same allocation using
MatmulImpl<A1,NZ>. All other shapes use the original GM Matmul kernel. Stage
the next A panel only after synchronous consumers and MTE1->MTE2 ordering.
This is actual A1 reuse, unlike a scheduler-only grouping probe. It also changes
task granularity, so gains cannot be attributed exclusively to L1 traffic.

The maximum explicit A panel is 65536 bytes. Matmul manages B/internal L1;
allocator coexistence, NZ stride, K/M/N tails, event lifetimes and external-A1
SetOrgShape semantics require compile/device validation. Small grouped grids
can reduce Cube parallelism. No official score or correctness status is
inherited from the parent. General numerical risks of the parent remain.

Baseline snapshot is supplied for paired diagnostics. No formal submissions
until required compilation/targeted checks succeed with no deterministic blocker.

## Compilation and qualification (2026-10-17)

- `a-l1-group4` compiled on CANN 9.1 / dav-2201; kernel hash
  a17beefe70a51228433bb51eff0224f8be9fbb3dd4c8934bd2c35f56fabb4bad.
  This initial probe is retained but not selected: full-M SetOrgShape is
  inconsistent with the physically staged 16-row NZ panel for multi-K blocks.
- `a-l1-group4-stride16` changes only the new kernel's SetOrgShape M to tileM,
  preserving full N for GM output row stride. Kernel hash
  431750131478b8b569b24d0f86e7fc224187d0ec87d81cf0eb4eac60f3fc249a.
  Revised candidate and exact baseline both compiled successfully; build logs
  reside in each candidate directory. Reproduction: run `prepare.py` in a fresh
  destination, then `revise_stride.py`; these scripts refuse existing outputs.
- `python3 optimization/candidates/dual-aiv-l1-v4/checks.py` passes 175 host
  ownership configurations, project hashes, and a pure host NZ offset model.
  These do not prove hardware layout or synchronization semantics.
- Requested strict smoke `17x1025x64` was refused before creating test inputs
  or launching a child because the host CAModel lease was busy. **No local
  device validation completed.** This is not a numerical or runtime failure
  of the candidate. Do not bypass the lock or run concurrently.
- Ready command after resource availability:
  `source env.sh Ascend910B1` then
  `python3 optimization/candidates/dual-aiv-l1-v4/checks.py --smoke --shape 17x1025x64`.
  It covers an M tail, five N tiles (including a tail and second group), two K
  blocks, signed scales and a zero row. Subsequently test `65x513x256`,
  `17x257x4096`, then the fallback `17x513x65`, each in its own shape directory.
  Use `--candidate baseline` for paired runs; compare only measured full-task
  cycles with matching fingerprints, not hypothetical stage latency.
- No formal submission and no new official score. Highest verified score
  remains 19.45. During the confirmed scoreboard freeze, a new passing result
  without attributable score may only be compared by official testcase IDs and
  times; it cannot trigger promotion. No root implementation was modified.

## Resumed qualification on the 19.45 parent

The `strict-current19-v1` run completed four serial strict INT32 CAModel tests:
`17x1025x64`, `65x513x256`, `17x257x4096`, and fallback `17x513x65`.
All had zero INT8 mismatches and exactly matching yScale (rtol=atol=1e-4).
Per-shape fingerprints and results are in
`a-l1-group4-stride16/results/strict-current19-v1/`. The host checks again
passed 175 ownership configurations and the NZ offset model. This supersedes
the earlier resource-busy note for these four cases only, not broad correctness.

Candidate kernel remains `431750131478b8b569b24d0f86e7fc224187d0ec87d81cf0eb4eac60f3fc249a`.
It is qualified for an independent formal submission. Root remains the verified
19.45 parent. Remaining risks include L1 allocator coexistence at other tilings,
different core counts and tails, small-grid underutilization, and inherited
large-K/FTZ numerical boundaries. No official performance improvement claimed.

## Formal feedback on the 19.45 parent

Submission `6ad345e2193e507d8ebb20ec` returned Pass, valid=true, 15/15 and
all precision_ratio=1 at 2026-10-17T09:55:24Z. Ranking is empty during the
user-confirmed freeze: no attributable official score, no promotion.
Recoverable upload, sanitized result and all 15 timing comparisons are in
`evidence/formal/dual-aiv-l1-6ad345e2-score-pending/`.
Against parent: 9 faster, 6 slower; adc7 -14.32%, adeb -5.72%, but adc3/adcb
+8.15%/+10.92%. Shapes and repeated-run variation unknown. Keep this direction
for controlled grouping/dispatch investigation; root stays unchanged.
