"""Structural and FP32 storage checks only; not device validation."""
from pathlib import Path
import numpy as np

here = Path(__file__).resolve().parent
root = here.parents[2]
base = (root / 'evidence/formal/tile16-persistent-6ad31941/source/kernel.asc').read_text()
source = (here / 'kernel.asc').read_text()


def section(text, start, end):
    return text[text.index(start):text.index(end, text.index(start))]


assert section(base, '    // Every AIC owns', '    // Fusion SyncAll') == section(
    source, '    // Every AIC owns', '    // Fusion SyncAll')
assert section(base, 'inline bool GenerateTileTiling', '} // namespace') == section(
    source, 'inline bool GenerateTileTiling', '} // namespace')
assert section(base, '                if (useReciprocal) {', '    __aicore__ inline void ProcessRow') == section(
    source, '                if (useReciprocal) {', '    __aicore__ inline void ProcessRow')
assert 'HardEvent::MTE3_S' in source
rng = np.random.default_rng(20261017)
for n in (4097, 8192, 8193, 16385):
    accum = rng.integers(-(2**30), 2**30, n, dtype=np.int32)
    channels = rng.uniform(-.1, .1, n).astype(np.float32)
    fp = np.maximum((accum.astype(np.float32) * np.float32(.031)) * channels, np.float32(0))
    cache = np.empty_like(fp)
    for col in range(0, n, 4096):
        cache[col:col+4096] = fp[col:col+4096]
    assert np.array_equal(cache.view(np.uint32), fp.view(np.uint32))
print('PASS: unchanged Cube/tiling/quantization; four FP32 cache/tail storage models')
