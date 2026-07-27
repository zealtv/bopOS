"""Durable parser tests for the numeric parameter automation grammar."""

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from paramgen import ParamGrammarError, parse_message  # noqa: E402


class ParamGrammarTests(unittest.TestCase):
    def test_static_set_and_fade_forms(self):
        static = parse_message([0.25], "f")
        self.assertEqual((static.kind, static.value), ("set", 0.25))

        implicit = parse_message([0.75, "250ms"], "f")
        self.assertEqual(implicit.kind, "fade")
        self.assertIsNone(implicit.start)
        self.assertEqual(implicit.segments, [(0.75, 250.0)])

        explicit = parse_message([0.25, 0.75, "2s", "c:1"], "f")
        self.assertEqual(explicit.kind, "fade")
        self.assertEqual(explicit.start, 0.25)
        self.assertEqual(explicit.segments, [(0.75, 2000.0)])
        self.assertEqual(explicit.curve, 1.0)

    def test_multi_segment_and_loop_forms(self):
        fade = parse_message([0.5, "1s", 1.0, "2s"], "f")
        self.assertEqual(fade.kind, "fade")
        self.assertEqual(fade.segments, [(0.5, 1000.0), (1.0, 2000.0)])

        loop = parse_message(["loop", 0.5, "1s", 1.0, "2s"], "f")
        self.assertEqual(loop.kind, "loop")
        self.assertEqual(loop.segments, fade.segments)

    def test_lfo_and_stop_forms(self):
        lfo = parse_message(
            ["lfo", "tri", 0, 1, "2s", "c:-1", "p:0.25", "free"],
            "i",
        )
        self.assertEqual(lfo.kind, "lfo")
        self.assertEqual(lfo.shape, "tri")
        self.assertEqual((lfo.minimum, lfo.maximum), (0.0, 1.0))
        self.assertEqual(lfo.period, 2000.0)
        self.assertEqual((lfo.curve, lfo.phase, lfo.free), (-1.0, 0.25, True))

        self.assertEqual(parse_message(["stop"], "f").kind, "stop")

    def test_automation_is_numeric_only(self):
        for param_type in ("s", "x", None):
            with self.subTest(param_type=param_type):
                with self.assertRaises(ParamGrammarError):
                    parse_message([1], param_type)

    def test_bad_grammar_is_rejected(self):
        cases = (
            [],
            ["stop", 1],
            ["lfo", "unknown", 0, 1, "1s"],
            ["lfo", "sine", 0, 1, 0],
            ["lfo", "sine", 0, 1, "1s", "p:2"],
            [0, 1, "bad-unit"],
            [1, "c:1"],
            ["loop"],
            [1, 2, "1s", "p:0.5"],
            [1, 2, "1s", "c:1", "curve:2"],
            [float("nan")],
            [True],
        )
        for args in cases:
            with self.subTest(args=args):
                with self.assertRaises(ParamGrammarError):
                    parse_message(list(args), "f")


if __name__ == "__main__":
    unittest.main()
