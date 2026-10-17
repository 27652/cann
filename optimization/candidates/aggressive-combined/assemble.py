"""Reproduce a narrow three-way merge from recoverable local sources."""
from pathlib import Path
import hashlib
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'evidence/formal/fast-track-6ad2dbba/source'
base = (BASE / 'kernel.asc').read_text()
assert hashlib.sha256(base.encode()).hexdigest() == 'b9a856aec216e11e8014a8808cc8f12be086a3dbf60831a3372c0d769a54a8a7'
tile = (HERE.parent / 'aggressive-tile-streaming/kernel.asc').read_text()
workspace = (HERE.parent / 'aggressive-workspace-launch/kernel.asc').read_text()

def section(text, start, end):
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b]

def transplant(text, donor, start, end):
    old = section(text, start, end)
    assert text.count(old) == 1
    return text.replace(old, section(donor, start, end), 1)

merged = transplant(base, tile, '    __aicore__ inline void Process()\n', '    matmul::Matmul<')
# Only the Vector scheduling wrapper changes, never arithmetic/quantization.
start = merged.index('class VectorStage')
prefix, vector = merged[:start], merged[start:]
vector = transplant(vector, tile[tile.index('class VectorStage'):],
                    '    __aicore__ inline void Process()\n',
                    'private:\n    __aicore__ inline void LoadAndActivate')
merged = prefix + vector
old = section(base, '    if ASCEND_IS_AIV {\n        // In MIX mode', '\n}\n\ninline bool GenerateMatmulTiling')
new = section(tile, '    if ASCEND_IS_AIV {\n        // The Matmul client', '\n}\n\ninline bool GenerateMatmulTiling')
assert merged.count(old) == 1
merged = merged.replace(old, new, 1)
helper = section(workspace, '// Shape-only single-element path.', '__global__ __aicore__ void quant_matmul_relu_quant_custom(')
merged = merged.replace('__global__ __aicore__ void quant_matmul_relu_quant_custom(', helper + '__global__ __aicore__ void quant_matmul_relu_quant_custom(', 1)
dispatch = section(workspace, '    if (M == 1U && N == 1U && K == 1U)', '    auto *platform =')
merged = merged.replace('    auto *platform =', dispatch + '    auto *platform =', 1)
for name in ('CMakeLists.txt', 'data_utils.h', 'main.asc', 'run.sh',
             'scripts/gen_data.py', 'scripts/QuantMatmulReluQuant.py', 'scripts/verify_result.py'):
    dest = HERE / name
    assert not dest.exists(), f'refusing overwrite: {dest}'
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BASE / name, dest)
assert not (HERE / 'kernel.asc').exists()
(HERE / 'kernel.asc').write_text(merged)
print(hashlib.sha256(merged.encode()).hexdigest())
