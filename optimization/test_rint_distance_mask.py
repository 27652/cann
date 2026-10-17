"""Host FP32 equivalence check, not a device precision certificate."""
import unittest
import numpy as np


class RintDistanceMaskTest(unittest.TestCase):
    def test_boundary_neighborhood_and_random(self):
        rng = np.random.default_rng(20261017)
        centers = np.arange(128, dtype=np.float32) + np.float32(0.5)
        # Include mask thresholds, ties and adjacent representable values.
        points = np.concatenate([centers, centers - np.float32(1/1024),
                                 centers + np.float32(1/1024)])
        neighborhoods = [points]
        lo, hi = points.copy(), points.copy()
        for _ in range(8):
            lo = np.nextafter(lo, np.float32(-np.inf))
            hi = np.nextafter(hi, np.float32(np.inf))
            neighborhoods.extend((lo.copy(), hi.copy()))
        q = np.concatenate([*neighborhoods,
                            rng.uniform(0, 128, 1000000).astype(np.float32),
                            np.arange(129, dtype=np.float32)])
        old = np.abs(q - (np.floor(q) + np.float32(0.5))) <= np.float32(1/1024)
        new = np.abs(q - np.rint(q)) >= np.float32(0.5 - 1/1024)
        np.testing.assert_array_equal(new, old)
        self.assertTrue(new[:128].all())


if __name__ == '__main__':
    unittest.main()
