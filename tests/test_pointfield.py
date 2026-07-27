"""Durable tests for point-plane parsing and node-side decomposition."""

import math
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

import pointfield  # noqa: E402


class PointWireTests(unittest.TestCase):
    def test_full_frame_is_atomic_and_zero_count_clears(self):
        self.assertEqual(
            pointfield.parse_wire(
                ["pt"],
                [2, 7, 1.0, 2.0, 3.0, pointfield.LINEAR,
                 9, 4.0, 5.0, 6.0, pointfield.SMOOTH],
            ),
            (
                "frame",
                {
                    7: (1.0, 2.0, 3.0, pointfield.LINEAR),
                    9: (4.0, 5.0, 6.0, pointfield.SMOOTH),
                },
            ),
        )
        self.assertEqual(
            pointfield.parse_wire(["pt"], [0]),
            ("frame", {}),
        )
        self.assertIsNone(
            pointfield.parse_wire(
                ["pt"], [2, 7, 1.0, 2.0, 3.0, 0, 9, "bad", 5.0, 6.0, 1]
            )
        )

    def test_sparse_and_clear_forms(self):
        self.assertEqual(
            pointfield.parse_wire(["pt"], [7, 1.0, 2.0, 3.0, 2]),
            ("set", (7, (1.0, 2.0, 3.0, pointfield.GAUSS))),
        )
        self.assertEqual(
            pointfield.parse_wire(["pt", "clear"], [7]),
            ("clear", 7),
        )

    def test_malformed_frames_are_rejected(self):
        cases = (
            ([], []),
            (["point"], [0]),
            (["pt"], []),
            (["pt"], [-1]),
            (["pt"], [2, 7, 1.0, 2.0, 3.0, 0]),
            (["pt"], [1, 7, math.inf, 2.0, 3.0, 0]),
            (["pt"], ["count"]),
        )
        for parts, args in cases:
            with self.subTest(parts=parts, args=args):
                self.assertIsNone(pointfield.parse_wire(parts, args))


class PointDecompositionTests(unittest.TestCase):
    def test_falloff_registry_and_bounds(self):
        self.assertEqual(pointfield.falloff(pointfield.LINEAR, 0, 4), 1.0)
        self.assertEqual(pointfield.falloff(pointfield.LINEAR, 4, 4), 0.0)
        self.assertEqual(pointfield.falloff(pointfield.LINEAR, 8, 4), 0.0)
        self.assertEqual(pointfield.falloff(pointfield.SMOOTH, 2, 4), 0.5)
        self.assertAlmostEqual(
            pointfield.falloff(pointfield.GAUSS, 4, 4),
            math.exp(-1),
        )
        self.assertEqual(pointfield.falloff(99, 2, 4), 0.5)
        self.assertEqual(pointfield.falloff(0, 0, 0), 0.0)

    def test_decomposition_is_sorted_and_zero_indexed(self):
        entries = pointfield.decompose(
            {
                9: (4.0, 0.0, 4.0, pointfield.LINEAR),
                2: (0.0, 0.0, 4.0, pointfield.LINEAR),
            },
            [[0.0, 0.0], [4.0, 0.0]],
        )
        self.assertEqual(
            entries,
            [
                (2, 0, 1.0),
                (2, 1, 0.0),
                (9, 0, 0.0),
                (9, 1, 1.0),
            ],
        )


if __name__ == "__main__":
    unittest.main()
