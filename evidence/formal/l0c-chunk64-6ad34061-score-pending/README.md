# L0C chunk64: formal testcase pass, score pending

Submission `6ad34061193e507d8eaf555b`, 2026-10-17. Received directly using
the reviewed CLI: Pass, valid=true, 15/15 and every precision_ratio=1.
The ranking snapshots returned no matching record. No official score is
claimed; this directory is NOT a validated scored-result bundle and must not
be used as a best-score baseline or promotion authority.

- `source/`: eight recoverable project context files, hashes in pending-result.
- `upload-manifest.json`: exact dynamic editable list and uploaded byte hashes;
  only kernel.asc was editable/uploaded.
- `pending-result.json`: sanitized exact-ID result and testcase timing data.
- `ranking-checks.json`: sanitized timestamped empty ranking query outcomes.
- `time-comparison.json`: all 15 testcase IDs aligned against verified 19.45
  dual-AIV baseline. Fourteen slower, one faster; timing-only feedback, not score.

Comparison observations: baseline result/ranking obtained 2026-10-17 09:10:55Z;
candidate final result obtained 09:31:52Z. These are stored result retrieval
times, not new network queries. Empty ranking does not independently establish
that the contest is sealed. Candidate and baseline differ in AIV architecture
as well as chunk handling, so no single-variable performance attribution is made.

Raw service response remains protected at
`/tmp/opencode/ownership-l0c-v3-l0c-result.json` (not committed).
Current scored best remains the independent dual-AIV 19.45 submission.
Next: obtain an official same-ID score, recover/validate a scored bundle using
formal_evidence.py, then compare; do not resubmit this unchanged payload.
