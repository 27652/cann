"""Host ownership checks; no device tiling API or instruction validation."""
import unittest


def partition(m, cores):
    target = 16 if m < 1024 else 128
    count = max(1, min(cores, (m + target - 1) // target))
    while count > 1:
        rows = ((m + count - 1) // count + target - 1) // target * target
        active = (m + rows - 1) // rows
        if active == count:
            break
        count = active
    rows = (m + count - 1) // count
    if count > 1:
        rows = (rows + target - 1) // target * target
    return count, rows


class RowParallelTest(unittest.TestCase):
    def test_complete_nonoverlapping_ownership(self):
        for m in (*range(1, 2049), 4095, 4096, 8193):
            for cores in (1, 2, 8, 20, 24, 32):
                count, rows = partition(m, cores)
                self.assertLessEqual(count, cores)
                self.assertEqual(count, (m + rows - 1) // rows)
                if count > 1:
                    self.assertEqual(rows % (16 if m < 1024 else 128), 0)
                intervals = [(i * rows, min((i + 1) * rows, m))
                             for i in range(count)]
                self.assertEqual(intervals[0][0], 0)
                self.assertEqual(intervals[-1][1], m)
                self.assertTrue(all(a < b for a, b in intervals))
                self.assertTrue(all(intervals[i][1] == intervals[i + 1][0]
                                    for i in range(count - 1)))


if __name__ == '__main__':
    unittest.main()
