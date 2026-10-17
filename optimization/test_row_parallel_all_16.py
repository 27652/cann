"""Host ownership model for the all-M INT8 16-row candidate; not device proof."""
import unittest
from pathlib import Path


def partition(m, cores, k):
    target = 16 if k < 65536 else 128
    count = 1 if m >= 1024 and k >= 65536 else max(1, min(cores, (m + target - 1) // target))
    if k < 65536:
        while count > 1:
            rows = ((m + count - 1) // count + target - 1) // target * target
            active = (m + rows - 1) // rows
            if active == count:
                break
            count = active
    rows = (m + count - 1) // count
    if k < 65536 and count > 1:
        rows = (rows + 15) // 16 * 16
    return count, rows


class AllRowsParallelTest(unittest.TestCase):
    def test_int8_ownership(self):
        values = (*range(1, 4097), 8191, 8192, 8193, 65535)
        for m in values:
            for cores in (1, 2, 8, 20, 24, 32):
                count, rows = partition(m, cores, 65535)
                self.assertLessEqual(count, cores)
                self.assertEqual(count, (m + rows - 1) // rows)
                self.assertGreater(m - (count - 1) * rows, 0)
                if count > 1:
                    self.assertEqual(rows % 16, 0)
        self.assertEqual(partition(1024, 24, 1024), (22, 48))
        self.assertEqual(partition(1024, 24, 65536), (1, 1024))

    def test_only_int8_partition_changes(self):
        root = Path(__file__).resolve().parents[1]
        old = (root / 'evidence/formal/fast-track-6ad2cf40/source/kernel.asc').read_text()
        new = (root / 'optimization/candidates/row-parallel-all-16/kernel.asc').read_text()
        self.assertEqual(old.split('inline bool GenerateMatmulTiling')[0],
                         new.split('inline bool GenerateMatmulTiling')[0])
        self.assertIn('if (alignedParallel) singleCoreM = AlignUpHost(singleCoreM, 16U);', new)
        self.assertIn('K < QuantMatmulReluQuant::FP32_MATMUL_K_THRESHOLD ? 16U : 128U;', new)


if __name__ == '__main__':
    unittest.main()
