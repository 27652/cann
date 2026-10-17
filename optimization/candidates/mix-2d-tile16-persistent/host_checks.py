"""Host/source invariants only; no claim about device instruction semantics."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
source = (HERE / 'kernel.asc').read_text()
baseline = (ROOT / 'evidence/formal/mix-2d-single-launch-6ad2ed99/source/kernel.asc').read_text()
old = 'const uint32_t tileM = std::min(64U, QuantMatmulReluQuant::AlignUpHost(M, 16U));'
new = 'const uint32_t tileM = std::min(16U, QuantMatmulReluQuant::AlignUpHost(M, 16U));'
assert baseline.count(old) == 1
assert source == baseline.replace(old, new), 'candidate must be a single-variable ablation'
start, end = 'class VectorStage {', '// Shape-only single-element path.'
assert source[source.index(start):source.index(end)] == baseline[baseline.index(start):baseline.index(end)]
dispatch = source[source.index('extern "C" void run_kernel'):]
active = dispatch[:dispatch.index('    // Split only M across cube cores.')]
assert active.count('<<<') == 2  # mutually exclusive single-element/general paths
special, general = active.split('    auto *platform', 1)
assert special.count('<<<') == 1 and 'return;' in special
assert general.count('<<<') == 1 and 'quant_mix_2d<<<' in general
assert 'quant_cube_2d<<<' not in source and 'quant_vector_rows<<<' not in source
kernel = source[source.index('__global__ __aicore__ void quant_mix_2d'):source.index('inline bool GenerateTileTiling')]
assert 'KERNEL_TYPE_MIX_AIC_1_1' in kernel and 'SPLIT_CORE_' not in kernel
assert kernel.count('SyncAll<false>()') == 1 and 'return;' not in kernel
assert kernel.index('mm.End();') < kernel.index('SyncAll<false>()') < kernel.index('stage.Init(')
assert 'physicalCap' in general and 'platform->GetCoreNumAic()' in general
count = 0
for m in (1, 2, 16, 17, 63, 64, 65, 129, 1024):
    for n in (1, 17, 255, 256, 257, 513, 1025, 4097):
        tm, tn = min(16, (m + 15) // 16 * 16), min(256, (n + 15) // 16 * 16)
        mt, nt = (m + tm - 1) // tm, (n + tn - 1) // tn
        for cap in (1, 2, 8, 20, 24):
            blocks = min(cap, mt * nt)
            tasks = [task for core in range(blocks) for task in range(core, mt * nt, blocks)]
            assert sorted(tasks) == list(range(mt * nt))
            area = 0
            for task in tasks:
                row, col = (task % mt) * tm, (task // mt) * tn
                rows, cols = min(tm, m - row), min(tn, n - col)
                assert 0 < rows <= tm and 0 < cols <= tn
                assert (row + rows - 1) * n + col + cols <= m * n
                area += rows * cols
            assert area == m * n
            owned = [row for core in range(blocks)
                     for row in range(m * core // blocks, m * (core + 1) // blocks)]
            assert owned == list(range(m))
            count += 1
for k in (1, 31, 65, 65535, 65536, 65537, 131072, 131073):
    parts = [min(65536, k - i) for i in range(0, k, 65536)]
    assert sum(parts) == k and all(p * 16384 <= 2**30 for p in parts)
record = {'scope': 'host source/layout only', 'status': 'passed',
          'ownership_configurations': count, 'k_chunk_configurations': 8,
          'kernel_sha256': hashlib.sha256(source.encode()).hexdigest(),
          'one_launch': 'exclusive single-element or MIX path; dead historical branch not executed',
          'device_numerics_and_barrier': 'not proven by this test'}
(HERE / 'host-checks.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
