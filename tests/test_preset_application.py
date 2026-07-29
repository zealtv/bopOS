"""Durable tests for the single preset application path."""

import copy
import datetime as dt
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
for source in (ROOT, ROOT / "python", ROOT / "dashboard"):
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))

import manifest  # noqa: E402
import preset_application  # noqa: E402
import preset_store  # noqa: E402
from osc_bridge import OSCBridge  # noqa: E402
from server import Dashboard  # noqa: E402
from state import InstallationState  # noqa: E402


class PresetApplicationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bopos-preset-apply-")
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
        self.dashboard.preset_store = preset_store.PresetStore(self.patches)

        async def broadcast(kind, data):
            self.broadcasts.append((kind, copy.deepcopy(data)))

        self.dashboard.broadcast = broadcast
        self.saved = 0
        real_save = self.state.save

        def counted_save():
            self.saved += 1
            real_save()

        self.state.save = counted_save
        self.now = dt.datetime(2026, 7, 29, 2, 3, 4, tzinfo=dt.timezone.utc)

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

    def save_preset(self, params, name="Dawn"):
        return self.dashboard.preset_store.save(
            "alpha", name, params, now=self.now)

    async def test_apply_skips_patch_mismatch_and_sends_timed_kinds_honestly(self):
        self.state.device_registry["two"]["desired_patch"] = {
            "name": "beta", "fingerprint": None}
        self.save_preset({
            "gain": [1.2345678],
            "count": [3.9],
            "gate": [1],
            "mode": [1],
            "voice": ["aah"],
            "wobble": ["lfo", "sine", 0.12345678, 0.87654321, "4s"],
            "gone": [0.5],
        })

        report = await self.dashboard.apply_preset(
            "alpha", "Dawn", "all", None, duration_ms=250, curve=1)

        self.assertEqual(self.saved, 1)
        # One persist, then the ordinary mirror publication every live write
        # makes, then the additive report. `07-control-device-ui` needs both:
        # the report says what the apply did, `state` is how a card learns the
        # new values and provenance.
        self.assertEqual([kind for kind, _payload in self.broadcasts],
                         ["state", "preset_applied"])
        self.assertTrue(self.sent)
        self.assertTrue(all(address.startswith("/1/") or address.startswith("/3/")
                            for address, _args in self.sent))
        self.assertFalse(any(address.startswith("/all/") for address, _args in self.sent))
        by_address = dict(self.sent)
        self.assertEqual(by_address["/1/p/gain"], [1.0, 250.0, "c:1"])
        self.assertEqual(by_address["/1/p/count"], [3, 250.0, "c:1"])
        self.assertEqual(by_address["/1/p/gate"], [1])
        self.assertEqual(by_address["/1/p/mode"], [1])
        self.assertEqual(by_address["/1/p/voice"], ["aah"])
        self.assertEqual(
            by_address["/1/p/wobble"],
            ["lfo", "sine", 0.123457, 0.876543, "4s"])
        self.assertNotIn("gain", self.state.seats["2"]["params"])
        self.assertEqual(self.state.seats["1"]["params"]["gain"], 1.0)
        self.assertEqual(self.state.seats["1"]["params"]["count"], 3)
        self.assertEqual(self.state.seats["1"]["applied_preset"],
                         {"patch": "alpha", "name": "Dawn"})
        self.assertNotIn("applied_preset", self.state.seats["2"])
        self.assertEqual(report["targets"]["2"]["skipped"], 1)
        self.assertEqual(report["targets"]["1"]["snapped"], 4)
        self.assertEqual(report["verdicts"]["gone"]["status"], "dropped")

    async def test_apply_coalesces_only_when_every_concrete_seat_survives(self):
        self.save_preset({"gain": [0.25]})
        await self.dashboard.apply_preset("alpha", "Dawn", "all", None)
        self.assertEqual(self.sent, [("/all/p/gain", [0.25])])
        self.assertEqual(
            [self.state.seats[key]["params"]["gain"] for key in ("1", "2", "3")],
            [0.25, 0.25, 0.25])

        self.sent.clear()
        await self.dashboard.apply_preset("alpha", "Dawn", "group", 1)
        self.assertEqual(self.sent, [("/g1/p/gain", [0.25])])

    async def test_apply_persist_failure_rolls_back_and_sends_nothing(self):
        self.save_preset({"gain": [0.25]})
        seat = self.state.seats["1"]
        seat["params"]["gain"] = 0.8
        seat["applied_preset"] = {"patch": "alpha", "name": "Old"}
        self.osc.automation["1"] = {
            "gain": {"args": ["lfo", "sine", 0, 1, "4s"],
                     "kind": "lfo", "sent_at": 10.0}}
        before_automation = copy.deepcopy(self.osc.automation)

        def fail_save():
            self.saved += 1
            raise OSError("disk full")

        self.state.save = fail_save
        with self.assertRaisesRegex(
                preset_store.PresetStoreError, "no command was sent"):
            await self.dashboard.apply_preset(
                "alpha", "Dawn", "seat", 1, duration_ms=100)

        self.assertEqual(self.saved, 1)
        self.assertEqual(self.sent, [])
        self.assertEqual(self.broadcasts, [])
        self.assertEqual(seat["params"]["gain"], 0.8)
        self.assertEqual(
            seat["applied_preset"], {"patch": "alpha", "name": "Old"})
        self.assertEqual(self.osc.automation, before_automation)

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

    def test_capture_projection_dirty_and_lowest_group_tie_break(self):
        seats = [self.state.seats["1"], self.state.seats["2"]]
        for seat in seats:
            seat["params"].update(gain=0.12345678, voice="aah", count=3)
            seat["applied_preset"] = {"patch": "alpha", "name": "Dawn"}
            seat["preset_dirty"] = False
        self.state.seats["1"]["params"]["gate"] = 0
        self.state.seats["2"]["params"]["gate"] = 1
        now = 200.0
        self.osc.automation["1"] = {
            "wobble": {"args": ["lfo", "sine", 0, 1, "4s"],
                       "kind": "lfo", "sent_at": 100.0}}
        self.osc.automation["2"] = copy.deepcopy(self.osc.automation["1"])

        captured = self.dashboard.capture_preset(
            "alpha", "group", 1, now=now)

        self.assertEqual(captured["params"]["gain"], [0.123457])
        self.assertEqual(captured["params"]["voice"], ["aah"])
        self.assertEqual(
            captured["params"]["wobble"], ["lfo", "sine", 0, 1, "4s"])
        self.assertIn("gate", captured["omitted"])
        self.assertEqual(captured["target"], {"scope": "group", "id": 1})
        self.assertEqual(
            self.dashboard.preset_card_projection("group", 1),
            {"preset": {"patch": "alpha", "name": "Dawn"},
             "dirty": False, "mixed": False})
        self.state.seats["2"]["applied_preset"] = {
            "patch": "alpha", "name": "Night"}
        self.assertTrue(
            self.dashboard.preset_card_projection("group", 1)["mixed"])

    def test_provenance_is_runtime_only_and_dirty_compares_canonical_state(self):
        self.save_preset({"gain": [0.123457]})
        seat = self.state.seats["1"]
        seat["params"]["gain"] = 0.12345678
        seat["applied_preset"] = {"patch": "alpha", "name": "Dawn"}
        self.dashboard.refresh_preset_dirtiness([seat], now=100)
        self.assertFalse(seat["preset_dirty"])
        seat["params"]["gain"] = 0.2
        self.dashboard.refresh_preset_dirtiness([seat], now=100)
        self.assertTrue(seat["preset_dirty"])
        durable = self.state.durable()["seats"]["1"]
        self.assertNotIn("applied_preset", durable)
        self.assertNotIn("preset_dirty", durable)


class PresetSurfaceServiceTests(PresetApplicationTests):
    """The host-side surface the Control, Device and editor rows consume."""

    async def test_catalog_lists_metadata_and_derives_schema_drift(self):
        self.save_preset({"gain": [0.5]}, name="Dawn")
        self.dashboard._editor_seat = {"id": 0, "automation_key": "editor",
                                       "editor": True, "bound": None,
                                       "groups": [], "params": {}}
        self.state.data["editor"] = {"patch": None}
        catalog = self.dashboard.preset_catalog()
        self.assertEqual([entry["slug"] for entry in catalog["alpha"]], ["Dawn"])
        entry = catalog["alpha"][0]
        # Metadata only: a listing never carries the stored parameter body.
        self.assertNotIn("params", entry)
        self.assertTrue(entry["valid"])
        self.assertFalse(entry["drift"])

        # Change the schema the preset was fingerprinted against.
        written, error = manifest.write_atomic(self.patches / "alpha", {
            "engine": "test", "entrypoint": "main.bin",
            "params": [{"name": "gain", "kind": "float", "min": 0, "max": 2}],
        })
        self.assertIsNone(error)
        self.assertIsNotNone(written)
        drifted = self.dashboard.preset_catalog()["alpha"][0]
        self.assertTrue(drifted["drift"])

    async def test_editor_target_is_selector_zero_but_not_seat_zero(self):
        """The editor's audition engine shares selector 0 with a Seat 0 on the
        wire, and nothing else: its durable mirror is the editor's own params
        map and its automation entries are keyed separately (08)."""
        self.dashboard._editor_seat = {"id": 0, "automation_key": "editor",
                                       "editor": True, "bound": None,
                                       "groups": [], "params": {}}
        self.state.data["editor"] = {"patch": "alpha", "params": {"gain": 0.25}}
        self.dashboard.set_supervisor_mode("edit")
        seats, selector = self.dashboard.live_param_target("editor", None)
        self.assertEqual(selector, 0)
        self.assertEqual(
            self.dashboard.effective_patch_for_seat(seats[0]), "alpha")
        # The params dict is shared by reference, so an apply writes straight
        # through to the state the editor panel renders.
        self.assertIs(seats[0]["params"], self.state.data["editor"]["params"])

        self.state.data["seats"]["0"] = self.seat(0, "zero")
        self.osc.record_param_for(
            seats, "gain", ["lfo", "sine", 0, 1, "4s"], sent_at=10)
        self.assertIn("editor", self.osc.automation)
        self.assertNotIn("0", self.osc.automation)

        self.dashboard.set_supervisor_mode("off")
        self.assertEqual(
            self.dashboard.live_param_target("editor", None), (None, None))


if __name__ == "__main__":
    unittest.main()
