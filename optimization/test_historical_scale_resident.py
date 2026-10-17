"""Host indexing/model smoke only; not AscendC execution or ISA validation."""
import unittest

import numpy as np

from int32_golden import int32_dot, reference


def resident_model(x1, x2, s1, s2, rows_per_core):
    acc = int32_dot(x1, x2)
    m, n = acc.shape
    y = np.empty((m, n), dtype=np.int8)
    ys = np.empty(m, dtype=np.float32)
    for first in range(0, m, rows_per_core):
        # Mirrors the candidate's ownership, pad and resident eligibility.
        resident = np.zeros((n + 7) // 8 * 8, np.float32) if n <= 4096 else None
        if resident is not None:
            resident[:n] = s2
        for row in range(first, min(first + rows_per_core, m)):
            activation = np.empty(n, np.float32)
            for col in range(0, n, 4096):
                end = min(col + 4096, n)
                scale = resident[:end-col] if resident is not None else s2[col:end].copy()
                activation[col:end] = np.maximum(
                    (acc[row, col:end].astype(np.float32) * s1[row]) * scale, 0.0)
            maximum = activation.max()
            ys[row] = maximum / np.float32(127) if maximum > 0 else np.float32(1)
            y[row] = np.clip(np.rint(activation / ys[row]), -128, 127).astype(np.int8)
    return y, ys


class ResidencyModelTest(unittest.TestCase):
    def test_partition_tail_and_scales(self):
        rng = np.random.default_rng(20261017)
        count = 0
        for m in (1, 5, 17):
            for n in (1, 7, 16, 17, 33, 256, 4095, 4096, 4097, 8193):
                x1 = rng.integers(-128, 128, (m, 7), dtype=np.int8)
                x2 = rng.integers(-128, 128, (n, 7), dtype=np.int8)
                x1[-1] = 0
                for mode in ('random', 'signed', 'tiny', 'zero'):
                    s1 = rng.uniform(0.1, 2, m).astype(np.float32)
                    s2 = rng.uniform(0.1, 2, n).astype(np.float32)
                    if mode == 'signed':
                        s1[::2] *= -1
                        s2[::2] *= -1
                    elif mode == 'tiny':
                        s2 *= np.float32(1e-38)
                    elif mode == 'zero':
                        s2[:] = 0
                    expected, scales, _ = reference(x1, x2, s1, s2)
                    for rows_per_core in (1, 3, 32):
                        with self.subTest(m=m, n=n, mode=mode, rows=rows_per_core):
                            actual, actual_scales = resident_model(x1, x2, s1, s2, rows_per_core)
                            np.testing.assert_array_equal(actual, expected)
                            np.testing.assert_array_equal(actual_scales.view(np.uint32),
                                                          scales.view(np.uint32))
                        count += 1
        self.assertEqual(count, 360)


if __name__ == '__main__':
    unittest.main()
