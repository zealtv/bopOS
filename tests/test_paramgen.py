"""Durable parser tests for the numeric parameter automation grammar."""

import sys
import math
import unittest
from unittest.mock import patch
from itertools import islice
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from paramgen import GeneratorEngine, ParamGrammarError, parse_message  # noqa: E402
from pythonosc.osc_message_builder import OscMessageBuilder


class ParamGrammarTests(unittest.TestCase):
    def test_explicit_start_loop_and_ignored_shorthands(self):
        self.assertEqual(parse_message(['loop', 0, 2, '60ms'], 'i').kind, 'loop')
        self.assertEqual(parse_message(['loop', 2], 'i').kind, 'set')
        self.assertEqual(parse_message(['loop', 2, '60ms'], 'i').kind, 'fade')

    def test_duration_conversion_is_finite(self):
        for duration in ('9' * 400 + 's', '9' * 305 + 'h', float('inf')):
            for args in ([1, duration], ['lfo', 'sine', 0, 1, duration]):
                with self.subTest(args=args), self.assertRaises(ParamGrammarError):
                    parse_message(args, 'f')

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


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.engine = GeneratorEngine(lambda *_: None, None, now_ns=lambda: 0)
        self.engine._running = False

    def fade(self, args, param_type='i', start=0):
        slot = self.engine._make_fade(parse_message(args, param_type), param_type, start, 0)
        self.engine._begin_fade(slot, 0)
        return slot

    def test_integer_reversal_within_tick(self):
        slot = self.fade([2, '10ms', 0, '10ms'])
        self.assertEqual(self.engine._advance_fade(slot, 30_000_000), [[1], [2], [1], [0]])
        self.assertEqual(slot['kind'], 'constant')

    def test_loop_finishes_segments_before_snap_and_catches_up(self):
        slot = self.fade(['loop', 2, '30ms', 4, '30ms'])
        self.assertEqual(self.engine._advance_fade(slot, 30_000_000), [[1], [2]])
        self.assertEqual(self.engine._advance_fade(slot, 180_000_000),
                         [[3], [4], [0]] + [[1], [2], [3], [4], [0]] * 2)

    def test_explicit_loops_repeat_for_both_types(self):
        for param_type in ('i', 'f'):
            with self.subTest(param_type=param_type):
                slot = self.fade(['loop', 0, 2, '60ms'], param_type)
                self.assertEqual(self.engine._advance_fade(slot, 120_000_000),
                                 [[1], [2], [0], [1], [2], [0]])
                self.assertEqual(slot['kind'], 'loop')

    def test_long_fades_do_not_precompute_events(self):
        # The old allocator is intercepted so the regression cannot exhaust RAM.
        with patch.object(self.engine, '_fade_events', create=True,
                          side_effect=AssertionError('eager fade allocation')):
            for param_type in ('i', 'f'):
                slot = self.fade([1, '1000000h'], param_type)
                self.assertNotIn('events', slot)
                self.engine._advance_fade(slot, 30_000_000)
            slot = self.fade([1, 1e308], 'f')
            self.assertEqual(self.engine._fade_value(slot, 0), 0)

    def test_crossings_are_lazy(self):
        crossings = self.engine._crossings(0, 100)
        self.assertNotIsInstance(crossings, list)
        self.assertEqual(list(islice(crossings, 3)), [[1], [2], [3]])
        self.assertEqual(list(islice(self.engine._crossings(-(2 ** 31), 2 ** 31 - 1), 3)),
                         [[-(2 ** 31) + value] for value in (1, 2, 3)])

    def test_large_crossings_resume_without_skips(self):
        slot = self.fade([2000, '1ms'])
        first = self.engine._advance_fade(slot, 30_000_000)
        self.assertLess(len(first), 2000)
        output = first
        for _ in range(100):
            if slot['kind'] == 'constant':
                break
            output += self.engine._advance_fade(slot, 30_000_000)
        self.assertEqual(output, [[value] for value in range(1, 2001)])
        self.assertEqual(slot['kind'], 'constant')

    def test_zero_duration_segments_and_loop_terminate(self):
        slot = self.fade(['loop', 2, 0, 0, 0])
        self.assertEqual(self.engine._advance_fade(slot, 0), [[1], [2], [1], [0]])
        self.assertEqual(slot['kind'], 'constant')

    def test_float_ticks_and_endpoints_stay_ordered(self):
        slot = self.fade([1, '35ms', 0, '10ms'], 'f')
        self.assertEqual(self.engine._advance_fade(slot, 17_000_000), [])
        self.assertEqual(slot['next_due'], 17_500_000)
        self.assertEqual(self.engine._advance_fade(slot, 35_000_000), [[.5], [1]])
        self.assertEqual(self.engine._advance_fade(slot, 45_000_000), [[0]])
        self.assertEqual(slot['value'], 0)

    def test_negative_fractional_crossings_and_curves(self):
        for curve in ('c:-2', 'c:0', 'c:2'):
            slot = self.fade([1.25, '10ms', -.25, '10ms', curve], start=-.25)
            self.assertEqual(self.engine._advance_fade(slot, 30_000_000),
                             [[0], [1], [0], [-1]])

    def test_replacement_discards_backlog_and_stop_uses_value_now(self):
        now = [0]
        output = []
        self.engine._now = lambda: now[0]
        self.engine._emit = lambda identity, args: output.append((identity, args))
        declaration = {'kind': 'int', 'default': 0}
        self.engine.apply('gain', parse_message([2000, '1ms'], 'i'), declaration)
        now[0] = 30_000_000
        slot = self.engine._slots['gain']
        self.assertLess(len(self.engine._advance_fade(slot, now[0])), 2000)
        self.assertEqual(self.engine.current_value('gain'), 2000)
        self.engine.apply('gain', parse_message(['stop'], 'i'), declaration)
        self.assertEqual(output, [('gain', [2000])])
        self.assertEqual(self.engine._slots['gain']['kind'], 'constant')
        self.engine.apply('gain', parse_message([7], 'i'), declaration)
        self.assertEqual(output[-1], ('gain', [7]))

    def test_stationary_short_loops_have_bounded_work(self):
        slot = self.fade(['loop', 0, 0, '1ms'])
        with patch.object(self.engine, '_value_steps', wraps=self.engine._value_steps) as steps:
            self.assertEqual(self.engine._advance_fade(slot, 1_000_000_000), [])
            self.assertLess(steps.call_count, 1000)
        self.assertEqual(slot['next_due'], 1_000_000_000)

    def test_loop_returning_to_start_does_not_duplicate_integer(self):
        slot = self.fade(['loop', 2, '10ms', 0, '10ms'])
        self.assertEqual(self.engine._advance_fade(slot, 40_000_000),
                         [[1], [2], [1], [0]] * 2)

    def test_lfo_turns_inside_tick(self):
        for shape in ('sine', 'tri', 'saw', 'square'):
            with self.subTest(shape=shape):
                spec = parse_message(['lfo', shape, 0, 2, '20ms'], 'i')
                slot = self.engine._make_lfo('gain', spec, 'i', 0)
                initial = self.engine._begin_lfo(slot, 0)
                output = self.engine._advance_lfo(slot, 40_000_000)
                expected = ([[1], [0], [1], [2]] * 2 if shape == 'square'
                            else [[1], [2], [1], [0]] * 2)
                self.assertEqual(output, expected)
                self.assertEqual(initial, [[2]] if shape == 'square' else [[0]])

    def test_random_lfos_visit_every_cycle(self):
        for shape in ('sh', 'drift'):
            slot = self.engine._make_lfo(
                'gain', parse_message(['lfo', shape, 0, 2, '20ms'], 'i'), 'i', 0)
            with patch.object(self.engine, '_random_value',
                              side_effect=lambda slot, cycle: 2 if cycle % 2 else 0):
                self.engine._begin_lfo(slot, 0)
                self.assertEqual(self.engine._advance_lfo(slot, 60_000_000),
                                 [[1], [2], [1], [0], [1], [2]])

    def test_lfo_phase_and_reverse_clock_boundaries(self):
        slot = self.engine._make_lfo(
            'gain', parse_message(['lfo', 'tri', 0, 4, '20ms', 'p:0.25'], 'i'), 'i', 0)
        self.engine._begin_lfo(slot, 0)
        self.assertEqual(self.engine._advance_lfo(slot, 20_000_000),
                         [[3], [4], [3], [2], [1], [0], [1], [2]])
        slot = self.engine._make_lfo(
            'gain', parse_message(['lfo', 'square', 0, 2, '20ms'], 'i'), 'i', 0)
        self.engine._begin_lfo(slot, 20_000_000)
        self.assertEqual(self.engine._advance_lfo(slot, 10_000_000), [[1], [0]])
        self.assertEqual(self.engine._advance_lfo(slot, 0), [[1], [2]])

    def test_lfo_large_backlog_resumes_and_close_stays_available(self):
        slot = self.engine._make_lfo(
            'gain', parse_message(['lfo', 'tri', 0, 2000, '20ms'], 'i'), 'i', 0)
        self.engine._begin_lfo(slot, 0)
        output = self.engine._advance_lfo(slot, 20_000_000)
        self.assertLess(len(output), 2000)
        for _ in range(100):
            if slot['next_due'] > 20_000_000:
                break
            output += self.engine._advance_lfo(slot, 20_000_000)
        self.assertEqual(output, [[value] for value in range(1, 2001)] +
                         [[value] for value in range(1999, -1, -1)])
        self.engine.close()


if __name__ == "__main__":
    unittest.main()
