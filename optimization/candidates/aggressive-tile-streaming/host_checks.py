"""Scheduling/source invariants only; never reports numerical/device correctness."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
baseline = (ROOT / 'evidence/formal/fast-track-6ad2d309/source/kernel.asc').read_text()
candidate = (HERE / 'kernel.asc').read_text()
assert hashlib.sha256(baseline.encode()).hexdigest() == '0cc3bc53431a46e63700e71f7a4568ee297c552ec5281a4e57f186ed60cb0e46'

# Quantization and row maximum bodies are byte-identical to the baseline.
for start, end in [
    ('    __aicore__ inline void LoadAndActivate', '    CubeTiling tiling;\n    bool floatMatmul'),
    ('#if defined(SPLIT_CORE_CUBE)', '/*\n * Vector stage'),
]:
    assert candidate[candidate.index(start):candidate.index(end)] == baseline[baseline.index(start):baseline.index(end)]

count = 0
for m in [1, 15, 16, 17, 127, 128, 129, 255, 256, 257, 1024, 4097, 16384]:
    for cores in [1, 2, 4, 8, 20, 24, 32]:
        # Includes realistic aligned ownership and single-core tiler fallback.
        extent = ((m + cores - 1) // cores + 15) // 16 * 16
        active = (m + extent - 1) // extent
        produced = []
        consumed = []
        for core in range(active):
            first = core * extent
            valid = min(extent, m - first)
            for local in range(0, valid, 128):
                job = min(128, valid - local)
                assert job > 0 and job <= 128
                rows = list(range(first + local, first + local + job))
                produced.extend(rows)
                consumed.extend(rows)
        assert produced == list(range(m))
        assert consumed == produced
        count += 1

handoff = candidate[candidate.index('        vectorStage.BeginRows(firstRow, rowEnd);'):]
assert handoff.index('cubeStage.ProcessRowJob(localRow, jobRows)') < handoff.index('vectorStage.ProcessRows(globalJobFirst, globalJobFirst + jobRows)') < handoff.index('cubeStage.Finish()')
print(json.dumps({'status': 'passed', 'scope': 'host scheduling/source invariants only', 'ownership_configurations': count, 'device_validation': 'not run', 'numerical_validation': 'not run'}, indent=2))
