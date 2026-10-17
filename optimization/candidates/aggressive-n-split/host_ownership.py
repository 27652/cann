#!/usr/bin/env python3
"""Host-only checks for the experimental N-shard partition geometry.

This does not exercise CANN tiling, device ownership, or kernel correctness.
"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
KERNEL = (ROOT / "kernel.asc").read_text()


def ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor


def align_up(value: int, alignment: int) -> int:
    return ceil_div(value, alignment) * alignment


def plan(m: int, n: int, k: int, cores: int) -> tuple[int, int]:
    """Mirror PlanNShards; returns (shard_count, shard_width)."""
    if not (m <= 32 and n >= 4096 and k < 65536 and cores > 1):
        return 1, n
    proposed = min(cores, ceil_div(n, 2048))
    width = align_up(ceil_div(n, proposed), 32)
    return ceil_div(n, width), width


class NShardOwnershipTests(unittest.TestCase):
    def test_dispatch_region_is_narrow_and_fallback_is_one_shard(self) -> None:
        for shape in ((1, 4095, 1, 32), (33, 8192, 1024, 32),
                      (8, 8192, 65536, 32), (8, 8192, 1024, 1)):
            self.assertEqual(plan(*shape), (1, shape[1]), msg=str(shape))
        self.assertGreater(plan(8, 8192, 1024, 8)[0], 1)

    def test_proposed_ranges_cover_n_without_overlap_or_holes(self) -> None:
        for m in range(1, 33):
            for n in (4096, 4097, 8191, 8192, 8193, 16384, 65535):
                for k in (1, 1024, 65535):
                    for cores in (2, 3, 4, 8, 16, 32, 64):
                        count, width = plan(m, n, k, cores)
                        spans = [(i * width, min(width, n - i * width))
                                 for i in range(count)]
                        self.assertEqual(spans[0][0], 0)
                        self.assertTrue(all(length > 0 for _, length in spans))
                        for previous, current in zip(spans, spans[1:]):
                            self.assertEqual(previous[0] + previous[1], current[0])
                        self.assertEqual(spans[-1][0] + spans[-1][1], n)

    def test_runtime_does_not_enable_prototype(self) -> None:
        helper = "GenerateNShardTilingPrototype"
        self.assertEqual(KERNEL.count(helper), 1,
                         "prototype should only be declared, not called")


if __name__ == "__main__":
    unittest.main(verbosity=2)
