# Final CLI verification and promotion

Submission `6ad345e2193e507d8ebb20ec`: Pass, valid=true, 15/15,
all precision_ratio=1. Same-ID ranking at 2026-10-17T10:08:02Z:
rank 195, official score 19.48 (previous verified best 19.45).

`evidence.json` and `source/` were recovered from the real CLI result and
same-ID ranking snapshot, with all eight project hashes checked. Actual
editable/uploaded file: kernel.asc; see `upload-manifest.json`.

Kernel SHA256: 431750131478b8b569b24d0f86e7fc224187d0ec87d81cf0eb4eac60f3fc249a.
Promoted root matches this exact source. Previous root is recoverable from
`../dual-aiv-fixed-6ad33b78/source/` and was unchanged before promotion.

Optimization: dual-AIV plus explicit A1/NZ 16xK panel reuse across up to four
adjacent N tiles, with stride16 SetOrgShape and original fallback.
No FIFO/chunk64 combination. 9 testcase times improve and 6 regress.
Full strict smoke evidence and earlier observations remain in the historical
`../dual-aiv-l1-6ad345e2-score-pending/` bundle (already committed).
General L1 tiling/tail/synchronization, large-K and FTZ/RNE boundary risks remain.

Raw CLI responses remain protected under `/tmp/opencode/final-archive-*`;
only allowlisted, sanitized evidence is versioned. No new submission was made.

Verification:
```sh
python3 evidence/formal_evidence.py validate evidence/formal/dual-aiv-l1-6ad345e2
python3 evidence/formal_evidence.py decide evidence/formal/dual-aiv-l1-6ad345e2 --best evidence/formal/dual-aiv-fixed-6ad33b78
```
