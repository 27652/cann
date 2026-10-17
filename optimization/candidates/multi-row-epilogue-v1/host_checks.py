"""Source identity and UB/layout bounds, not a device numerical proof."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
base = (ROOT / 'evidence/formal/tile16-persistent-6ad31941/source/kernel.asc').read_text()
source = (HERE / 'kernel.asc').read_text()
macro = '#ifndef QUANT_MULTI_ROW\n#define QUANT_MULTI_ROW 4U\n#endif\n'
normalized = source.replace(macro, '')
assert normalized[:normalized.index('class VectorStage {')] == base[:base.index('class VectorStage {')]
tail = '// Shape-only single-element path.'
assert source[source.index(tail):] == base[base.index(tail):]
def quant_body(text):
    start = text.index('    __aicore__ inline void QuantizeRow(')
    end = text.index('    __aicore__ inline void ProcessRow(', start)
    return text[start:end]
assert quant_body(source).replace('bool isZeroRow, uint32_t fpOffset = 0U)',
                                'bool isZeroRow)').replace(
    'fpBuffer.Get<float>()[fpOffset]', 'fpBuffer.Get<float>()') == quant_body(base)
cases = 0
for rows in (2, 4, 8):
    for n in range(1, 4096 // rows + 1):
        stride = (n + 63) // 64 * 64
        parts = stride // 64
        partial_stride = (parts + 7) // 8 * 8
        assert rows * stride <= 4096
        assert rows * partial_stride <= 4096
        assert stride - n < 64 and parts <= 64
        assert rows <= 32
        cases += 1
print(json.dumps({'status': 'passed', 'layout_cases': cases,
                  'checks': ['Cube/prefix identity', 'dispatch/workspace identity',
                             'quantization body identity modulo fp slice', 'group UB bounds'],
                  'source_sha256': hashlib.sha256(source.encode()).hexdigest()}))
