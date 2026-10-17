"""Candidate host diagnostics only: does not execute AscendC instructions."""
from pathlib import Path
import hashlib
import json
import numpy as np

rng = np.random.default_rng(20261017)
checks = 0
for m in (*range(1, 4097), 8193, 65535):
    for cores in (1, 2, 8, 20, 24, 32):
        count = max(1, min(cores, (m + 15) // 16))
        while count > 1:
            rows = ((m + count - 1) // count + 15) // 16 * 16
            active = (m + rows - 1) // rows
            if active == count:
                break
            count = active
        rows = (m + count - 1) // count
        if count > 1:
            rows = (rows + 15) // 16 * 16
        assert count == (m + rows - 1) // rows and count <= cores
        assert count == 1 or rows % 16 == 0
        checks += 1

lanes = 0
for exponent in range(-126, 100):
    scale = np.float32(np.ldexp(1.125, exponent))
    q = rng.uniform(0, 127, 8192).astype(np.float32)
    a = (q * scale).astype(np.float32)
    exact = (a / scale).astype(np.float32)
    approx = ((a * np.float32(1.0 / scale)).astype(np.float32)
              if scale > np.float32(1e-30) else exact)
    hint = np.rint(approx)
    risk = np.abs(approx - hint) >= np.float32(0.5 - 1 / 1024)
    assert np.all(hint[~risk] == np.rint(exact[~risk]))
    lanes += len(q)

source = Path(__file__).with_name('kernel.asc')
print(json.dumps(dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                      ownership_checks=checks, ieee_mask_lanes=lanes,
                      device_validation=False,
                      limitation='IEEE host arithmetic; not an FTZ or device-accuracy proof')))
