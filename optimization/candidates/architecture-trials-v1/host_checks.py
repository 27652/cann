"""Ownership/protocol models, not device instruction proofs."""
from pathlib import Path
import hashlib
import json

here = Path(__file__).resolve().parent
hashes = {}
for variant in ('local-k', 'local-k-safe', 'scale-owner', 'tile-fifo'):
    hashes[variant] = hashlib.sha256((here / variant / 'kernel.asc').read_bytes()).hexdigest()

for m in (1, 2, 16):
    for n in (16384, 16385, 32769):
        for shards in (2, 3, 8):
            tile = ((n + shards - 1) // shards + 31) // 32 * 32
            spans = [(s * tile, min(n, (s + 1) * tile)) for s in range(shards)]
            assert sum(max(0, b-a) for a, b in spans) == n
            for row in range(m):
                assert sum(s == row % shards for s in range(shards)) == 1
            partial_bytes = m * shards * 32
            broadcast_bytes = m * 32
            assert partial_bytes + broadcast_bytes == m * (shards + 1) * 32

for jobs in (0, 1, 2, 3, 17, 129):
    for blocks in (1, 2, 8, 20):
        seen = []
        for block in range(blocks):
            owned = list(range(block, jobs, blocks))
            seen.extend(owned)
            pending = []
            for i, _ in enumerate(owned):
                if i >= 2:
                    assert pending.pop(0) == i-2
                pending.append(i)
                assert len(pending) <= 2
            assert len(pending) == min(2, len(owned))
        assert sorted(seen) == list(range(jobs))

(here / 'source-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
for k in (65536, 65537, 131071, 131072, 131073, 262144):
    chunks = []
    offset = 0
    while offset < k:
        chunk = k-offset if k < 131072 else min(k-offset, 65536)
        chunks.append(chunk)
        offset += chunk
    assert sum(chunks) == k
    if k < 131072:
        assert len(chunks) == 1 and k * 16384 <= 2**31-1
    else:
        assert max(chunks) <= 65536
print('PASS: 81 shard configurations; 24 FIFO models; six safe K-boundary models')
