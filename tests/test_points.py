"""Host point boundaries and silence after a completed motion."""
import asyncio
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))
import points
from osc_bridge import OSCBridge


class PointAuthoringTests(unittest.TestCase):
    def test_invalid_ids_are_rejected(self):
        for value in (float("inf"), float("nan"), 2**31, -1, 0.9, True, [], 10**400):
            with self.subTest(value=value):
                self.assertIsNone(points.sanitize_point({"id": value}))
        self.assertEqual(points.sanitize_point({"id": 2**31 - 1})["id"], 2**31 - 1)

    def test_malformed_optional_values_fall_back(self):
        for value in ([], {}, float("inf"), 10**400):
            with self.subTest(value=value):
                point = points.sanitize_point({"id": 0, "falloff": value,
                    "x": value, "motion": {"type": "path", "points": value}})
                self.assertEqual(point["falloff"], points.DEFAULT_FALLOFF)
                self.assertNotIn("motion", point)

    def test_unwireable_path_coordinates_are_dropped(self):
        for value in (1e39, 10**400):
            point = points.sanitize_point({"id": 0, "motion": {
                "type": "path", "points": [[value, 0]]}})
            self.assertNotIn("motion", point)

    def test_malformed_room_uses_finite_defaults(self):
        point = points.sanitize_point({"id": 0}, {"width": [], "depth": 10**400})
        self.assertEqual((point["x"], point["y"]), (5.0, 4.0))


class PointLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_endpoint_sent_once_then_silence(self):
        point = points.sanitize_point({"id": 0, "motion": {
            "type": "path", "points": [[0, 0], [1, 2]], "duration": 1}})
        point["motion"]["started"] = 5.0
        bridge = OSCBridge.__new__(OSCBridge)
        bridge.state = types.SimpleNamespace(data={"points": {0: point}})
        bridge._points_started = 0.0
        frames, browser_frames = [], []
        bridge.send = lambda address, args: frames.append(args)
        bridge.broadcast = lambda kind, payload: browser_frames.append(payload)
        clock = [5.0]
        ticks = iter((5.5, 6.1, 7.0, 8.0))

        async def tick(_delay):
            try:
                clock[0] = next(ticks)
            except StopIteration:
                raise asyncio.CancelledError

        with patch("osc_bridge.asyncio.sleep", tick), patch("osc_bridge.time.monotonic", lambda: clock[0]):
            await bridge.points_loop()
        self.assertEqual([frame[2:4] for frame in frames], [[0.5, 1.0], [1.0, 2.0]])
        self.assertEqual(len(browser_frames), 2)

    def test_continuous_motions_stay_dynamic(self):
        for motion in (
            {"type": "path", "points": [[0, 0], [1, 1]], "loop": True},
            {"type": "orbit", "center": [0, 0]},
            {"type": "bounce"},
        ):
            self.assertTrue(points.is_dynamic(points.sanitize_point({"id": 0, "motion": motion}), 10000))
