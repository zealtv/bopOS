"""Durable tests for the shared live parameter replay and automation."""

import copy
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
for source in (ROOT, ROOT / "python", ROOT / "dashboard"):
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))

import manifest  # noqa: E402
import live_params  # noqa: E402
from osc_bridge import OSCBridge  # noqa: E402
from python.paramgen import GeneratorEngine, parse_message  # noqa: E402
from server import Dashboard  # noqa: E402
from state import InstallationState  # noqa: E402


class LiveParameterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bopos-live-params-")
        self.root = Path(self.temp.name)
        self.patches = self.root / "patches"
        self.alpha = self.make_patch("alpha", [
            {"name": "gain", "kind": "float", "min": 0, "max": 1},
            {"name": "count", "kind": "int", "min": 0, "max": 8},
            {"name": "gate", "kind": "toggle"},
            {"name": "mode", "kind": "enum", "options": ["dry", "wet"]},
            {"name": "voice", "kind": "text"},
            {"name": "wobble", "kind": "float", "min": 0, "max": 1},
        ])
        self.make_patch("beta", [
            {"name": "gain", "kind": "float", "min": -1, "max": 1},
        ])
        self.state = InstallationState(str(self.root / "state.json"))
        self.state.data["seats"] = {
            "1": self.seat(1, "one"),
            "2": self.seat(2, "two"),
            "3": self.seat(3, "three"),
        }
        self.state.data["groups"] = {
            "2": {"id": 2, "name": "Pair B"},
            "1": {"id": 1, "name": "Pair A"},
        }
        self.state.seats["1"]["groups"] = [1, 2]
        self.state.seats["2"]["groups"] = [1, 2]
        self.state.data["device_registry"] = {
            uid: {"uid": uid, "alias": uid, "device_enabled": True}
            for uid in ("one", "two", "three")
        }
        self.state.data["devices"] = {
            uid: self.state._runtime_device(uid) for uid in ("one", "two", "three")
        }
        for uid, device in self.state.devices.items():
            seat = self.state.seat_for_uid(uid)
            device["id"] = seat["id"]
        self.state.data["fleet_patch"] = {"name": "alpha", "fingerprint": "sha256:x"}
        self.state.data["params_patch"] = "alpha"
        self.sent = []
        self.broadcasts = []
        self.osc = OSCBridge(self.state, lambda *_args: None, 0, 0, "127.0.0.1")
        self.osc.send = lambda address, args=(): self.sent.append(
            (address, copy.deepcopy(list(args))))
        self.dashboard = Dashboard.__new__(Dashboard)
        self.dashboard.state = self.state
        self.dashboard.osc = self.osc
        self.dashboard.patches_dir = str(self.patches)

        async def broadcast(kind, data=None):
            self.broadcasts.append((kind, copy.deepcopy(data)))

        self.dashboard.broadcast = broadcast
        self.saved = 0
        real_save = self.state.save

        def counted_save():
            self.saved += 1
            real_save()

        self.state.save = counted_save


    def tearDown(self):
        self.temp.cleanup()


    @staticmethod
    def seat(seat_id, uid):
        return {
            "id": seat_id, "name": uid, "positions": [], "params": {},
            "groups": [], "bound": uid,
        }


    def make_patch(self, name, params):
        path = self.patches / name
        path.mkdir(parents=True)
        (path / "main.bin").write_bytes(b"engine")
        written, error = manifest.write_atomic(path, {
            "engine": "test", "entrypoint": "main.bin", "params": params,
        })
        self.assertIsNone(error)
        return written


    def test_replay_derives_fade_expiry_and_preserves_generator_timestamps(self):
        seat = self.state.seats["1"]
        seat["params"].update(gain=0.8, count=7, wobble=0.4)
        old = time.time() - 2
        lfo_sent = time.time() - 100
        self.osc.automation["1"] = {
            "gain": {"args": [0.8, "100ms"], "kind": "fade",
                     "from": 0.1, "sent_at": old},
            "count": {"args": ["loop", 1, "1s", 7, "1s"], "kind": "loop",
                      "sent_at": lfo_sent},
            "wobble": {"args": ["lfo", "sine", 0, 1, "4s"], "kind": "lfo",
                       "sent_at": lfo_sent, "phase_at_send_ms": 125},
        }
        before = copy.deepcopy(self.osc.automation)

        self.dashboard.replay_live_params_for_seat(seat)

        messages = dict(self.sent)
        self.assertEqual(messages["/1/p/gain"], [0.8])
        self.assertEqual(messages["/1/p/count"], ["loop", 1, "1s", 7, "1s"])
        self.assertEqual(messages["/1/p/wobble"], ["lfo", "sine", 0, 1, "4s"])
        self.assertEqual(self.osc.automation, before)


    def test_stop_estimate_writes_one_canonical_durable_value(self):
        seat = self.state.seats["1"]
        declaration = self.dashboard.live_param_declaration("gain", "alpha")
        self.osc.automation["1"] = {
            "gain": {"args": [1, "1s"], "kind": "fade",
                     "from": 0, "sent_at": 100.0}}

        changed = self.dashboard.store_stopped_automation(
            [seat], declaration, now=100.3333333)

        self.assertTrue(changed)
        self.assertEqual(self.saved, 1)
        self.assertEqual(seat["params"]["gain"], 0.333333)
        self.assertEqual(self.state.devices["one"]["params"]["gain"], 0.333333)


    def test_fade_takeover_origin_matches_node_live_value(self):
        """The dashboard mirror must take over where the node generator is."""
        declaration = self.dashboard.live_param_declaration("gain", "alpha")

        for label, initial_args, elapsed_s in (
                ("static", [0.2], 0.25),
                ("mid-fade", [1.0, "1s"], 0.25),
                ("mid-lfo", ["lfo", "sine", 0.0, 1.0, "1s"], 0.25)):
            with self.subTest(label=label):
                node_now_ns = [100_000_000_000]
                node = GeneratorEngine(
                    lambda *_args: None, None, now_ns=lambda: node_now_ns[0])
                seat = self.seat(1, "one")
                seat["params"]["gain"] = 0.2
                self.osc.automation.clear()
                try:
                    node.apply("gain", parse_message([0.2], "f"), declaration)
                    with mock.patch(
                            "osc_bridge.time.monotonic_ns",
                            return_value=node_now_ns[0]):
                        self.osc.record_param_for(
                            [seat], "gain", initial_args, sent_at=1000.0,
                            persist=False, broadcast=False)
                    node.apply(
                        "gain", parse_message(initial_args, "f"), declaration)
                    node_now_ns[0] += int(elapsed_s * 1_000_000_000)
                    expected = node.current_value("gain")

                    with mock.patch(
                            "osc_bridge.time.monotonic_ns",
                            return_value=node_now_ns[0]):
                        self.osc.record_param_for(
                            [seat], "gain", [0.8, "1s"],
                            sent_at=1000.0 + elapsed_s,
                            persist=False, broadcast=False)

                    self.assertAlmostEqual(
                        self.osc.automation["1"]["gain"]["from"],
                        expected, places=6)
                finally:
                    node.close()


    def test_stop_command_survives_argument_canonicalization(self):
        declaration = self.dashboard.live_param_declaration("gain", "alpha")

        self.assertEqual(
            live_params.canonicalize_args(declaration, ["stop"]),
            ["stop"])
