"""Read-only source/ownership checks. Not a device instruction proof."""
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def frozen(name):
    directory = HERE / name
    hashes = json.loads((directory / 'submit-project-hashes.json').read_text())
    for filename, digest in hashes.items():
        assert hashlib.sha256((directory / 'submit-project' / filename).read_bytes()).hexdigest() == digest
    source = (directory / 'kernel.asc').read_text()
    assert source.encode() == (directory / 'submit-project/kernel.asc').read_bytes()
    return source, hashes['kernel.asc']


scale, scale_hash = frozen('scale-owner')
assert 'if (shard != row % shardCount) continue;' in scale
assert 'if (shardMode) { AscendC::SyncAll<false>(); AscendC::SyncAll<false>(); }' in scale
section = scale[scale.index('    __aicore__ inline void ProcessShardRows'):scale.index('    __aicore__ inline void EndRows')]
assert section.count('AscendC::SyncAll<false>();') == 2
assert 'static_cast<uint64_t>(M) * (vectorShards + 1U) * 32ULL' in scale
scale_cases = 0
for m in (1, 2, 3, 7, 16):
    for n in (16384, 16385, 32767, 32769, 65537):
        for blocks in (1, 2, 3, 8, 20, 32):
            shards = min(blocks, 8, n // 2048)
            if shards == 1:
                continue
            stride = ((n + shards - 1) // shards + 31) // 32 * 32
            spans = [(s * stride, min(n, (s + 1) * stride)) for s in range(shards)]
            assert spans[0][0] == 0 and spans[-1][1] == n
            assert all(a < b for a, b in spans)
            assert all(spans[s][1] == spans[s+1][0] for s in range(shards-1))
            assert all(a % 32 == 0 for a, _ in spans)
            for row in range(m):
                owners = [s for s in range(shards) if s == row % shards]
                assert len(owners) == 1
                partial = {(row * shards + s) * 32 for s in range(shards)}
                metadata = m * shards * 32 + row * 32
                assert max(partial) + 32 <= m * shards * 32 <= metadata
                assert metadata + 32 <= m * (shards + 1) * 32
            # All MIX halves participate even for idle AIV blocks.
            assert [3 for _ in range(blocks)] == [1+2 for _ in range(blocks)]
            scale_cases += 1

fifo, fifo_hash = frozen('tile-fifo')
assert 'const bool useRowRing = M >= 1024U && N <= 4096U;' in fifo
assert 'if (i >= 2U) AscendC::CrossCoreWaitFlag(6U + slot);' in fifo
assert 'AscendC::PipeBarrier<PIPE_ALL>();' in fifo
assert 'AscendC::CrossCoreSetFlag<0x2, PIPE_MTE2>(6U + slot);' in fifo
fifo_cases = 0
for m in (1024, 1025, 1039, 2049, 4097):
    for n in (1, 33, 257, 513, 4096):
        for cap in (1, 2, 3, 8, 20, 32):
            jobs = (m + 15) // 16
            blocks = min(cap, jobs)
            seen = Counter()
            for block in range(blocks):
                owned = list(range(block, jobs, blocks))
                ready, free = [], []
                outstanding = {}
                for i, job in enumerate(owned):
                    slot = i % 2
                    if i >= 2:
                        assert outstanding.pop(slot) == i-2
                        free.append(i-2)
                    assert slot not in outstanding
                    outstanding[slot] = i
                    ready.append(i)
                    start, end = job * 16, min(m, (job+1)*16)
                    seen.update(range(start, end))
                    assert (end-start)*n*4 <= 16*n*4
                drain = list(range(max(0,len(owned)-2), len(owned)))
                for i in drain:
                    assert outstanding.pop(i % 2) == i
                    free.append(i)
                assert not outstanding and ready == free
            assert seen == Counter({row: 1 for row in range(m)})
            fifo_cases += 1

print(json.dumps({'status': 'passed', 'scale_owner_configurations': scale_cases,
                  'fifo_configurations': fifo_cases,
                  'source_sha256': {'scale-owner': scale_hash, 'tile-fifo': fifo_hash},
                  'scope': 'frozen hashes, source invariants, host ownership/protocol models; not device proof'}))
