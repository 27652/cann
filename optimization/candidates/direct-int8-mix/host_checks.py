"""Host layout/source checks, not device or numerical validation."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
baseline = (ROOT / 'evidence/formal/fast-track-6ad2e0a8/source/kernel.asc').read_text()
candidate = (HERE / 'kernel.asc').read_text()
assert hashlib.sha256(baseline.encode()).hexdigest() == 'e763bfe2fe3682de621febc73b7889539f6a1d686188eb8a27bb619755ac81ea'
for start, end in [
    ('class VectorStage {', '// Shape-only single-element path.'),
    ('inline bool GenerateMatmulTiling', '} // namespace QuantMatmulReluQuant'),
    ('extern "C" void run_kernel', None),
]:
    b = baseline[baseline.index(start):baseline.index(end) if end else None]
    c = candidate[candidate.index(start):candidate.index(end) if end else None]
    assert b == c
count = 0
for m in [1, 15, 16, 17, 127, 128, 129, 257, 1024, 4097]:
    for cores in [1, 2, 4, 8, 20, 24, 32]:
        extent = ((m + cores - 1) // cores + 15) // 16 * 16
        active = (m + extent - 1) // extent
        produced = []
        for core in range(active):
            start = core * extent
            valid = min(extent, m - start)
            for local in range(0, valid, 128):
                rows = min(128, valid - local)
                produced.extend(range(start + local, start + local + rows))
        assert produced == list(range(m))
        count += 1
for k in [1, 31, 32, 65535, 65536, 65537, 131071, 131072, 131073, 262145]:
    chunks = [(offset, min(65536, k - offset)) for offset in range(0, k, 65536)]
    assert sum(n for _, n in chunks) == k
    assert all(0 < n <= 65536 and n * 16384 <= 2**30 for _, n in chunks)
    assert [offset for offset, _ in chunks] == list(range(0, k, 65536))
    count += 1
direct = candidate[candidate.index('class DirectInt8CubeStage'):candidate.index('#if defined(SPLIT_CORE_CUBE)')]
assert direct.index('matmul.End();') < direct.index('AscendC::NotifyEvent<PIPE_FIX>(5);')
dispatch = candidate[candidate.index('    // INT8 uses the direct MIX producer.'):candidate.index('    CubeStage cubeStage;', candidate.index('    // INT8 uses the direct MIX producer.'))]
assert dispatch.index('AscendC::WaitEvent(5);') < dispatch.index('vectorStage.Process();')
print(json.dumps({'status': 'passed', 'scope': 'host source/layout only',
                  'configurations': count, 'device_validation': 'not run',
                  'numerical_validation': 'not run'}, indent=2))
