"""Check ownership and unchanged arithmetic, not device numerical semantics."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
base = (ROOT / 'evidence/formal/tile16-persistent-6ad31941/source/kernel.asc').read_text()
source = (HERE / 'submit-project/kernel.asc').read_text()
begin = '        for (uint64_t task = block; task < taskCount; task += blocks) {'
stop = '        mm.End();'
base_start = base.index(begin)
source_start = source.index('        // Consecutive N tiles of an A row panel')
assert base[:base_start] == source[:source_start]
assert base[base.index(stop, base_start):] == source[source.index(stop, source_start):]
body_start = '            const uint32_t rows = tiling.M - row < tileM'
body_end = '                k += chunk;\n            }'
for text in (base, source):
    assert text.count(body_start) == 1
b = base.index(body_start)
s = source.index(body_start)
assert base[b:base.index(body_end, b)+len(body_end)] == source[s:source.index(body_end, s)+len(body_end)]
count = 0
for m in (1, 2, 3, 16, 17, 64, 129):
    for n in (1, 2, 3, 4, 5, 7, 8, 9, 17, 65):
        for blocks in (1, 2, 3, 8, 20, 32):
            blocks = min(blocks, m*n)
            groups = m*((n+3)//4)
            grouped = groups >= blocks and n > 1
            tasks = []
            for block in range(blocks):
                for work in range(block, groups if grouped else m*n, blocks):
                    first = (work//m)*4 if grouped else work//m
                    end = min(first+4, n) if grouped else first+1
                    tasks.extend((work % m, col) for col in range(first, end))
            assert len(tasks) == m*n and len(set(tasks)) == m*n
            assert set(tasks) == {(r,c) for r in range(m) for c in range(n)}
            count += 1
hashes = json.loads((HERE / 'project-hashes.json').read_text())
for name, expected in hashes.items():
    assert hashlib.sha256((HERE / 'submit-project' / name).read_bytes()).hexdigest() == expected
print(json.dumps({'status':'passed', 'ownership_configurations':count,
                  'unchanged':['quantization', 'Cube tile arithmetic', 'dispatch',
                               'workspace', 'SyncAll', 'single launch'],
                  'kernel_sha256':hashes['kernel.asc']}))
