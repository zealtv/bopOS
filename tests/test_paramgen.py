"""Durable parser tests for the numeric parameter automation grammar."""

import sys
import math
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from paramgen import GeneratorEngine, ParamGrammarError, parse_message  # noqa: E402
from pythonosc.osc_message_builder import OscMessageBuilder


class ParamGrammarTests(unittest.TestCase):
    def test_generator_interpolation_stays_serializable_at_scalar_edges(self):
        engine = GeneratorEngine(lambda *_: None, None, now_ns=lambda: 0)
        float_max = 3.4028234663852886e38
        for param_type, low, high in (('f', -float_max, float_max),
                                      ('i', -(2 ** 31), 2 ** 31 - 1)):
            fade = engine._make_fade(
                parse_message([low, high, '60ms'], param_type), param_type, low, 0)
            for shape in ('sine', 'tri', 'saw', 'square', 'sh', 'drift'):
                lfo = engine._make_lfo(
                    'gain', parse_message(['lfo', shape, low, high, '60ms'], param_type),
                    param_type, 0)
                for now in (0, 15_000_000, 30_000_000, 45_000_000, 60_000_000):
                    for value in (engine._fade_value(fade, now), engine._lfo_value(lfo, now)):
                        self.assertTrue(math.isfinite(value))
                        message = OscMessageBuilder(address='/p/gain')
                        message.add_arg(math.floor(value) if param_type == 'i' else value,
                                        param_type)
                        self.assertTrue(message.build().dgram)

    def test_generator_values_fit_the_declared_wire_scalar(self):
        for param_type, value in (('f', 1e100), ('f', -1e100),
                                  ('f', 10 ** 400), ('i', 2 ** 31),
                                  ('i', -(2 ** 31) - .5), ('i', 10 ** 400)):
            for args in ([value], [value, '1ms'], [value, 0, '1ms'],
                         ['lfo', 'sine', 0, value, '1s']):
                with self.subTest(param_type=param_type, args=args):
                    with self.assertRaises(ParamGrammarError):
                        parse_message(args, param_type)
        for param_type, value in (('f', 3.4028234663852886e38),
                                  ('i', -(2 ** 31)), ('i', 2 ** 31 - 1),
                                  ('i', 1.75), ('i', -.25)):
            spec = parse_message([value], param_type)
            message = OscMessageBuilder(address='/p/gain')
            message.add_arg(math.floor(spec.value) if param_type == 'i' else spec.value,
                            param_type)
            self.assertTrue(message.build().dgram)

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
