#!/usr/bin/env python3
"""Focused regression verifier for the ratified Seats workspace."""

import asyncio
import copy
import json
import sys
import tempfile
from pathlib import Path
from types import MethodType
import unittest

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "tools" / "simfleet.py").exists():
            return parent
    raise RuntimeError("could not locate repository root")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "dashboard"))

from osc_bridge import OSCBridge  # noqa: E402
from server import Dashboard  # noqa: E402
from state import InstallationState  # noqa: E402


def seat(seat_id, uid=None, name=None):
    return {"id": seat_id, "name": name or f"Seat {seat_id}",
            "positions": [[float(seat_id), 1.0]], "params": {}, "bound": uid}


class StateTests(unittest.TestCase):
    def make_state(self, directory):
        return InstallationState(str(Path(directory) / "installation.json"))

    def test_load_rejects_mismatched_key_and_duplicate_binding(self):
        cases = [
            {"4": seat(5, "node-a")},
            {"4": seat(4, "node-a"), "5": seat(5, "node-a")},
        ]
        for seats in cases:
            with self.subTest(seats=seats), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "installation.json"
                path.write_text(json.dumps({"schema": 1, "name": "invalid",
                                             "seats": seats}), encoding="utf-8")
                state = InstallationState(str(path))
                self.assertTrue(state._load_invalid)
                self.assertEqual({}, state.seats)
                self.assertEqual("bopOS", state.data["name"])

    def test_seat_ids_reject_bool_and_fractional_values(self):
        with tempfile.TemporaryDirectory() as directory:
            state = self.make_state(directory)
            for value in (True, False, 1.0, 1.5, "1.5"):
                with self.subTest(value=value):
                    self.assertIsNone(state.clean_seat_id(value))
                    self.assertIsNone(state.clean_seat({
                        "id": value, "name": "invalid", "positions": []}))

    def test_reindex_migrates_current_presets_but_not_saved_venue(self):
        with tempfile.TemporaryDirectory() as directory:
            state = self.make_state(directory)
            state.data["seats"] = {"2": seat(2, "node-a")}
            state.data["presets"] = {
                "show": {"seats": {"2": {"gain": 0.4}}, "note": "preserve"},
                "empty": {"seats": {}},
            }
            state.save_venue("before-reindex")

            result, error = state.reindex_seat(2, 8)

            self.assertIsNone(error)
            self.assertEqual(8, result["id"])
            self.assertNotIn("2", state.seats)
            self.assertEqual({"gain": 0.4}, state.data["presets"]["show"]["seats"]["8"])
            self.assertEqual("preserve", state.data["presets"]["show"]["note"])
            venue = json.loads((Path(directory) / "installations" /
                                "before-reindex.json").read_text(encoding="utf-8"))
            self.assertIn("2", venue["seats"])
            self.assertNotIn("8", venue["seats"])

    def test_reindex_rejects_collision_and_rolls_back_failed_save(self):
        with tempfile.TemporaryDirectory() as directory:
            state = self.make_state(directory)
            state.data["seats"] = {"2": seat(2), "8": seat(8)}
            state.data["presets"] = {"show": {"seats": {"2": {"gain": 1}}}}
            before = copy.deepcopy(state.data)
            result, error = state.reindex_seat(2, 8)
            self.assertIsNone(result)
            self.assertIn("already exists", error)
            self.assertEqual(before, state.data)

            del state.data["seats"]["8"]
            before = copy.deepcopy(state.data)
            original_save = state.save
            state.save = lambda: (_ for _ in ()).throw(OSError("disk full"))
            try:
                result, error = state.reindex_seat(2, 9)
            finally:
                state.save = original_save
            self.assertIsNone(result)
            self.assertIn("no changes", error)
            self.assertEqual(before, state.data)

    def test_delete_cleans_every_current_preset_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            state = self.make_state(directory)
            state.data["seats"] = {"2": seat(2), "3": seat(3)}
            state.data["presets"] = {
                "a": {"seats": {"2": {"gain": 0.2}, "3": {"gain": 0.3}}},
                "b": {"seats": {"2": {"gain": 0.8}}},
            }
            deleted = state.delete_seat(2)
            self.assertEqual(2, deleted["id"])
            self.assertNotIn("2", state.seats)
            self.assertNotIn("2", state.data["presets"]["a"]["seats"])
            self.assertNotIn("2", state.data["presets"]["b"]["seats"])
            self.assertIn("3", state.data["presets"]["a"]["seats"])

    def test_venue_keeps_offline_remembered_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            state = self.make_state(directory)
            state.data["seats"] = {"7": seat(7, "offline-node")}
            state.save_venue("offline")
            state.data["seats"] = {}
            self.assertTrue(state.load_venue("offline"))
            self.assertEqual("offline-node", state.seats["7"]["bound"])
            self.assertEqual([{"id": 7, "uid": "offline-node"}],
                             state.last_venue_rebind["waiting"])


class FakeOSC:
    def __init__(self, state, responses=()):
        self.state = state
        self.responses = list(responses)
        self.events = []
        self.before_unassign = None

    async def unassign(self, uid):
        self.events.append(("unassign", uid))
        if self.before_unassign:
            self.before_unassign(uid)
        return self.responses.pop(0) if self.responses else True

    def assign(self, uid, seat_id, name, positions):
        self.events.append(("assign", uid, seat_id))

    def request(self, uid, member):
        self.events.append(("request", uid, member))

    def send_audition_listener(self):
        self.events.append(("listener",))


class ServerMutationTests(unittest.IsolatedAsyncioTestCase):
    def make_dashboard(self, directory, responses=()):
        dashboard = Dashboard.__new__(Dashboard)
        dashboard.state = InstallationState(str(Path(directory) / "installation.json"))
        dashboard.state.data["supervisor"] = {"mode": "off"}
        dashboard.state.data["editor"] = {"active": False}
        dashboard.supervisor_lock = asyncio.Lock()
        dashboard.osc = FakeOSC(dashboard.state, responses)
        dashboard.messages = []
        dashboard.errors = []
        dashboard.replays = 0

        async def broadcast(this, kind, data):
            this.messages.append((kind, copy.deepcopy(data)))

        async def ws_error(this, ws, message):
            this.errors.append(message)

        def replay(this):
            this.replays += 1

        dashboard.broadcast = MethodType(broadcast, dashboard)
        dashboard.ws_error = MethodType(ws_error, dashboard)
        dashboard.replay_current_assignments = MethodType(replay, dashboard)
        return dashboard

    @staticmethod
    def add_device(state, uid, online=True):
        device = state.ensure(uid)
        device.update(online=online, virtual=False, hostname=uid)
        return device

    async def test_remove_waits_for_ack_and_timeout_is_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            dashboard = self.make_dashboard(directory, [False])
            dashboard.state.data["seats"] = {"1": seat(1, "node-a")}
            self.add_device(dashboard.state, "node-a")
            dashboard.osc.before_unassign = lambda uid: self.assertEqual(
                "node-a", dashboard.state.seats["1"]["bound"])

            await dashboard.handle_ws({"type": "remove_seat", "data": {"id": 1}})

            self.assertIn("1", dashboard.state.seats)
            self.assertTrue(any("No dashboard state changed" in error
                                for error in dashboard.errors))
            self.assertEqual([("unassign", "node-a")], dashboard.osc.events)

            dashboard.osc.responses = [True]
            await dashboard.handle_ws({"type": "remove_seat", "data": {"id": 1}})
            self.assertNotIn("1", dashboard.state.seats)

    async def test_unbind_and_replacement_revoke_before_mutating(self):
        with tempfile.TemporaryDirectory() as directory:
            dashboard = self.make_dashboard(directory, [True, True])
            dashboard.state.data["seats"] = {
                "1": seat(1, "node-a"), "2": seat(2, "node-b")}
            self.add_device(dashboard.state, "node-a")
            self.add_device(dashboard.state, "node-b")
            observed = []
            dashboard.osc.before_unassign = lambda uid: observed.append(
                (uid, dashboard.state.seats["1"]["bound"],
                 dashboard.state.seats["2"]["bound"]))

            await dashboard.handle_ws({"type": "unbind_seat", "data": {"id": 1}})
            self.assertEqual(("node-a", "node-a", "node-b"), observed[0])
            self.assertIsNone(dashboard.state.seats["1"]["bound"])

            # Restore an occupied target so this operation simultaneously
            # displaces node-a and moves node-b from Seat 2.
            dashboard.state.seats["1"]["bound"] = "node-a"
            await dashboard.handle_ws({"type": "bind_seat", "data": {
                "id": 1, "uid": "node-b", "confirmed": True}})
            self.assertEqual(("node-a", "node-a", "node-b"), observed[1])
            self.assertEqual(("node-b", "node-a", "node-b"), observed[2])
            self.assertEqual([("unassign", "node-a"), ("unassign", "node-a"),
                              ("unassign", "node-b")], dashboard.osc.events[:3])
            self.assertEqual("node-b", dashboard.state.seats["1"]["bound"])
            self.assertIsNone(dashboard.state.seats["2"]["bound"])
            bindings = [item["bound"] for item in dashboard.state.seats.values()
                        if item["bound"]]
            self.assertEqual(len(bindings), len(set(bindings)))

    async def test_binding_conflict_requires_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            dashboard = self.make_dashboard(directory)
            dashboard.state.data["seats"] = {
                "1": seat(1, None), "2": seat(2, "node-b")}
            self.add_device(dashboard.state, "node-b")
            before = copy.deepcopy(dashboard.state.seats)
            await dashboard.handle_ws({"type": "bind_seat", "data": {
                "id": 1, "uid": "node-b"}})
            self.assertEqual(before, dashboard.state.seats)
            self.assertTrue(any("confirm" in error for error in dashboard.errors))

    async def test_offline_displacement_stays_quarantined_after_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            dashboard = self.make_dashboard(directory)
            dashboard.state.data["seats"] = {"1": seat(1, "node-a")}
            device = self.add_device(dashboard.state, "node-a", online=False)

            await dashboard.handle_ws({"type": "unbind_seat", "data": {"id": 1}})

            self.assertIsNone(dashboard.state.seats["1"]["bound"])
            self.assertTrue(device["revoking_assignment"])
            self.assertEqual([], dashboard.osc.events)

    async def test_venue_timeout_leaves_dashboard_state_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            dashboard = self.make_dashboard(directory, [True, False])
            state = dashboard.state
            state.data["seats"] = {
                "1": seat(1, "node-c"), "2": seat(2, None)}
            state.save_venue("target")
            state.data["seats"] = {
                "1": seat(1, "node-a"), "2": seat(2, "node-b")}
            self.add_device(state, "node-a")
            self.add_device(state, "node-b")
            before = copy.deepcopy(state.data)
            dashboard.osc.before_unassign = lambda uid: self.assertEqual(
                before["seats"], state.data["seats"])

            await dashboard.handle_ws({"type": "load_venue", "data": {
                "name": "target"}})

            self.assertEqual(before, state.data)
            self.assertEqual([("unassign", "node-a"), ("unassign", "node-b")],
                             dashboard.osc.events)
            self.assertEqual(1, dashboard.replays)


class BridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_stale_unbound_heartbeat_is_quarantined_until_minus_one(self):
        with tempfile.TemporaryDirectory() as directory:
            state = InstallationState(str(Path(directory) / "installation.json"))
            state.data["supervisor"] = {"mode": "off"}
            events = []
            bridge = OSCBridge(state, lambda kind, data: events.append((kind, data)),
                               0, 0, "127.0.0.1")
            commands = []
            requests = []
            bridge.uid_command = lambda uid, verb, args=(): commands.append((uid, verb))
            bridge.request = lambda uid, member: requests.append((uid, member))

            # SUPERSEDED by 23-waveform-marker-guard-regression: every non-virtual
            # heartbeat is now a mute-convergence edge too (`d23bba0`, "Complete
            # Dashboard live controls" -- persistent exact-UID device mute), so the
            # raw command list also carries ("uid", "mute"). These assertions are
            # about the UNASSIGN handshake -- that it is sent once and not replayed
            # -- so they filter to that verb rather than pinning the whole list and
            # breaking on every additive convergence verb that follows.
            unassigns = lambda: [item for item in commands if item[1] == "unassign"]

            bridge.handle("/hb", ["node-stale", 6, "1.5", 1, -40], "10.0.0.6")
            device = state.devices["node-stale"]
            self.assertEqual(-1, device["id"])
            self.assertTrue(device["revoking_assignment"])
            self.assertEqual([("node-stale", "unassign")], unassigns())

            bridge.handle("/hb", ["node-stale", -1, "1.5", 1, -40], "10.0.0.6")
            self.assertFalse(device["revoking_assignment"])
            self.assertEqual(-1, device["id"])
            self.assertEqual([("node-stale", "unassign")], unassigns())

    async def test_offline_moved_binding_revokes_then_assigns_on_reconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            state = InstallationState(str(Path(directory) / "installation.json"))
            state.data["supervisor"] = {"mode": "off"}
            state.data["seats"] = {"8": seat(8, "node-moved")}
            device = state.ensure("node-moved")
            device["revoking_assignment"] = True
            bridge = OSCBridge(state, lambda kind, data: None, 0, 0, "127.0.0.1")
            commands, assignments = [], []
            bridge.uid_command = lambda uid, verb, args=(): commands.append((uid, verb))
            bridge.assign = lambda uid, seat_id, name, positions: assignments.append((uid, seat_id))
            bridge.request = lambda uid, member: None

            # SUPERSEDED by 23-waveform-marker-guard-regression: every non-virtual
            # heartbeat is now a mute-convergence edge too (`d23bba0`, "Complete
            # Dashboard live controls" -- persistent exact-UID device mute), so the
            # raw command list also carries ("uid", "mute"). These assertions are
            # about the UNASSIGN handshake -- that it is sent once and not replayed
            # -- so they filter to that verb rather than pinning the whole list and
            # breaking on every additive convergence verb that follows.
            unassigns = lambda: [item for item in commands if item[1] == "unassign"]

            bridge.handle("/hb", ["node-moved", 3, "1.5", 1], "10.0.0.8")
            self.assertEqual([("node-moved", "unassign")], unassigns())
            self.assertEqual([], assignments)
            self.assertTrue(device["revoking_assignment"])

            bridge.handle("/hb", ["node-moved", -1, "1.5", 1], "10.0.0.8")
            self.assertFalse(device["revoking_assignment"])
            self.assertIn(("node-moved", 8), assignments)


class UIBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "dashboard" / "static" / "index.html").read_text(
            encoding="utf-8")
        cls.js = (ROOT / "dashboard" / "static" / "js" / "dashboard.js").read_text(
            encoding="utf-8")

    def function_body(self, start, end):
        return self.js.split(start, 1)[1].split(end, 1)[0]

    def test_seats_tab_owns_workspace_and_map_first_controls(self):
        seats_html = self.html.split('id="tab-seats"', 1)[1].split(
            'id="tab-devices"', 1)[0]
        self.assertIn('id="spatial"', seats_html)
        self.assertIn('id="seat-add"', seats_html)
        self.assertIn('id="seat-detail"', seats_html)
        body = self.function_body("function renderSeatDetail()", "function renderDeviceDetail()")
        for selector in ("seat-name", "seat-reindex", "seat-remove", "seat-device",
                         "seat-identify", "seat-bind", "seat-unbind"):
            self.assertIn(selector, body)
        self.assertIn("filter(device=>!device.virtual)", body)
        self.assertIn("!device.revoking_assignment", body)

    def test_devices_detail_has_no_editable_seat_or_parameter_surface(self):
        body = self.function_body("function renderDeviceDetail()", "function bindDeviceDetailControls")
        for forbidden in ('id="seat-name"', 'id="seat-id"', 'id="seat-device"',
                          'data-param=', "Position</h2>", "Params</h2>"):
            self.assertNotIn(forbidden, body)
        # SUPERSEDED by 23-waveform-marker-guard-regression: this used to scrape the
        # sentence "Seat naming, IDs, positions and assignment live in the Seats
        # workspace." `149c794` ("Polish Dashboard hierarchy and diagnostics") cut it
        # in the terse-copy pass, which was deliberate. The point of the check is
        # that the Devices detail still POINTS AT the Seats workspace rather than
        # duplicating it, so it now asserts the durable affordances that do that --
        # a structural anchor ages better than a sentence.
        self.assertIn('id="device-open-seat"', body)
        self.assertIn("Seat transaction", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
