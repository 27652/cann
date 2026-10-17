# Small-M 16-row ownership candidate (2026-10-17)

Baseline: official submission `6ad2cb6b193e507d8e02c24b`, score 11.80,
kernel SHA256 `007b6fb9ba6f55d5033f644fcc6cc6c975666ea9dd7d1c4d08bca9e38b674aab`.

Hypothesis: 128-row core allocation underutilizes hardware for M <= 128.
For M < 1024 and K < 65536, use 16-row aligned M partitions, fix up the
active core count, and reject changed tiling ownership boundaries. Keep N
complete per core. On tiling failure, retry a single-core tiling. Large-M and
FP32-conversion paths retain their original partition choices.

This does not establish which official testcases use small M. In particular,
the large gaps at points 7 and 11 have no confirmed shape/path attribution.

Source SHA256: `23d1d79ea003e5f8818f016a851d289758f93520971c820875a9b96ec0403923`.
CANN 9.1.0 / dav-2201 Release build passed. Staging binary SHA256:
`a01a7aab818b3390c19f6d07a7ef24bb1dbd98e5fe65e8db3eff580e7e4f00ea`.
Staging/logs/frozen manifest:
`/tmp/opencode/cannjudge-fast-track-audit-20261017/row-parallel-16/`.

Host tests passed:
`PYTHONPATH=optimization python3 -m unittest optimization.test_row_parallel_16 optimization.test_historical_scale_resident -v`.
Partition model covers 2051 M values and six hardware core counts, checking
alignment, active counts and contiguous nonempty intervals. It does not invoke
the device tiling API or execute AscendC. **No local device validation completed.**
Risks: device tiling ownership, multicore tail writes and synchronization;
inherited mask error bounds/FTZ, resident tensor lifetime and large-K FP32 behavior.

One formal POST attempt returned HTTP 429 (retry after 104 seconds).
No submission ID or official score obtained; no automatic retry performed.
The candidate is NOT promoted. Root remains the baseline 11.80 payload.
