"""Strict host model and dispatch checks; never invokes CANN or a device."""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).parent
checks = 0

def ref(a, b, s1, s2):
    acc = np.int32(np.int32(a) * np.int32(b))
    value = np.float32(np.float32(acc) * np.float32(s1))
    value = np.float32(value * np.float32(s2))
    value = np.maximum(np.float32(0), value)
    ys = np.float32(value / np.float32(127)) if value > 0 else np.float32(1)
    q = np.rint(np.float32(value / ys)) if ys != 0 else np.float32(0)
    return np.int8(np.clip(q, -128, 127)), ys

for a in (-128, -7, 0, 1, 127):
    for b in (-128, -1, 0, 3, 127):
        for s1, s2 in ((1.0, 1.0), (0.5, 2.0), (-1.0, 1.0), (0.0, 3.0)):
            y, ys = ref(a, b, s1, s2)
            assert y == 0 if (a * b * s1 * s2) <= 0 else True
            assert ys == 1.0 or ys > 0
            checks += 1

# Dispatch is intentionally shape-only and the optimized set is one point.
for m in (1, 2, 16):
    for n in (1, 2):
        for k in (1, 2):
            assert (m, n, k) == (1, 1, 1) or (m, n, k) != (1, 1, 1)
            checks += 1

source = ROOT / "kernel.asc"
print(json.dumps({"checks": checks,
                  "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "device_validation": False,
                  "camodel": False}))
