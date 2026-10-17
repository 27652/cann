"""Ownership and MIX barrier checks; not device correctness evidence."""
from pathlib import Path

count = 0
for n in (8192, 8193, 16384, 65537):
    for blocks in (2, 3, 8, 20, 24, 32):
        tile = ((n + blocks - 1) // blocks + 31) // 32 * 32
        ranges = [(s * tile, min((s + 1) * tile, n)) for s in range(blocks)]
        coverage = [0] * n
        for begin, end in ranges:
            assert begin % 32 == 0
            for column in range(begin, end):
                coverage[column] += 1
        assert all(value == 1 for value in coverage)
        count += 1
source = Path(__file__).with_name('kernel.asc').read_text()
assert 'partial.SetValue(' not in source
assert 'QuantizeRow(row, tokenScale, outputScale, rowMax == 0.0f, begin, end)' in source
assert 'if (shardMode) AscendC::SyncAll<false>();' in source
print(f'PASS: {count} N-partition ownership configurations; source protocol invariants')
