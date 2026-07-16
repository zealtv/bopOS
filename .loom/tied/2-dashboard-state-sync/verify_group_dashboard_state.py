#!/usr/bin/env python3
"""Focused dashboard state and fake-transport checks for Seat groups."""

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
        if (parent / "dashboard" / "server.py").is_file():
            return parent
    raise RuntimeError("could not locate repository root")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "dashboard"))

from osc_bridge import OSCBridge  # noqa: E402
from pythonosc.osc_message import OscMessage  # noqa: E402
from server import Dashboard  # noqa: E402
from state import InstallationState  # noqa: E402


def seat(seat_id, groups=(), uid=None, params=None):
    return {"id": seat_id, "name": f"Seat {seat_id}",
            "positions": [[float(seat_id), 1.0]], "params": dict(params or {}),
            "groups": list(groups), "bound": uid}


class StateTests(unittest.TestCase):
    def make_state(self, directory):
        return InstallationState(str(Path(directory) / "installation.json"))

    def test_catalog_membership_validation_and_deterministic_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            state = self.make_state(directory)
            front, error = state.create_group(" Front row ")
            self.assertIsNone(error)
            guitars, error = state.create_group("Guitars")
            self.assertIsNone(error)
            self.assertEqual((0, "Front row"), (front["id"], front["name"]))
            self.assertEqual(1, guitars["id"])
            self.assertEqual({}, state.seats)
            state.data["seats"] = {"2": seat(2, [1, 0])}
            cleaned = state.clean_seats(state.data["seats"])
            self.assertEqual([0, 1], cleaned["2"]["groups"])
            self.assertIsNone(state.clean_group_ids([0, 0]))
            self.assertIsNone(state.clean_group_ids([2147483648]))
            self.assertIsNone(state.clean_seats({"3": seat(3, [7])}))
            self.assertIsNone(state.clean_next_group_id(True, state.data["groups"]))
            self.assertIsNone(state.clean_next_group_id(1, state.data["groups"]))
            self.assertIsNone(state.clean_next_group_id(
                2147483649, state.data["groups"]))

    def test_multiple_empty_groups_delete_cleanup_and_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            state = self.make_state(directory)
            for name in ("Front", "Back", "Empty"):
                self.assertIsNone(state.create_group(name)[1])
            state.data["seats"] = {
                "1": seat(1, [0, 1]), "2": seat(2, [1]), "3": seat(3, [])}
            removed, error = state.delete_group(1)
            self.assertIsNone(error)
            self.assertEqual("Back", removed["name"])
            self.assertEqual([0], state.seats["1"]["groups"])
            self.assertEqual([], state.seats["2"]["groups"])
            self.assertIn("2", state.data["groups"])
            replacement, error = state.create_group("Replacement")
            self.assertIsNone(error)
            self.assertEqual(3, replacement["id"])
            self.assertNotIn("1", state.data["groups"])
            reloaded = self.make_state(directory)
            self.assertEqual(4, reloaded.data["next_group_id"])
            after_reload, error = reloaded.create_group("After reload")
            self.assertIsNone(error)
            self.assertEqual(4, after_reload["id"])
            before = copy.deepcopy(state.data)
            original = state.save
            state.save = lambda: (_ for _ in ()).throw(OSError("disk full"))
            try:
                result, error = state.set_seat_groups(1, [2])
            finally:
                state.save = original
            self.assertIsNone(result)
            self.assertIn("no changes", error)
            self.assertEqual(before, state.data)

    def test_venue_round_trip_and_preset_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            state = self.make_state(directory)
            state.data["groups"] = {"4": {"id": 4, "name": "Choir"}}
            state.data["next_group_id"] = 5
            state.data["seats"] = {"7": seat(7, [4], None, {"gain": .4})}
            state.data["presets"] = {"quiet": {
                "master": .5, "seats": {"7": {"gain": .2}}}}
            state.save_venue("grouped")
            snapshot = json.loads((Path(directory) / "installations" /
                                   "grouped.json").read_text(encoding="utf-8"))
            self.assertEqual({"4": {"id": 4, "name": "Choir"}}, snapshot["groups"])
            self.assertEqual([4], snapshot["seats"]["7"]["groups"])
            self.assertNotIn("groups", snapshot["presets"]["quiet"])
            later, error = state.create_group("Later")
            self.assertIsNone(error)
            self.assertEqual(5, later["id"])
            state.data["groups"] = {}
            state.data["seats"] = {}
            self.assertTrue(state.load_venue("grouped"))
            self.assertEqual([4], state.seats["7"]["groups"])
            self.assertEqual(6, state.data["next_group_id"])
            after_load, error = state.create_group("After venue load")
            self.assertIsNone(error)
            self.assertEqual(6, after_load["id"])


class FakeSender:
    def __init__(self):
        self.frames = []

    def sendto(self, data, destination):
        message = OscMessage(data)
        self.frames.append((message.address, list(message.params), destination))

    def close(self):
        pass


class BridgeTests(unittest.IsolatedAsyncioTestCase):
    def setup_bridge(self, directory):
        state = InstallationState(str(Path(directory) / "installation.json"))
        state.data["groups"] = {
            "0": {"id": 0, "name": "Front"}, "2": {"id": 2, "name": "Guitars"}}
        state.data["next_group_id"] = 3
        state.data["seats"] = {
            "1": seat(1, [0, 2], "node-a", {"fx/reverb/gain": .1}),
            "2": seat(2, [2], None, {"fx/reverb/gain": .2}),
            "3": seat(3, [0], "node-b", {"fx/reverb/gain": .3}),
        }
        node = state.ensure("node-a")
        node.update(id=1, ip="10.0.0.1", online=True)
        offline = state.ensure("node-b")
        offline.update(id=3, ip="10.0.0.2", online=False)
        events = []
        bridge = OSCBridge(state, lambda kind, data: events.append((kind, data)),
                           0, 16660, "127.0.0.1")
        bridge.sender = FakeSender()
        return state, bridge, events

    async def test_exact_stale_receipts_retry_exhaustion_and_report_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            state, bridge, _events = self.setup_bridge(directory)
            self.assertTrue(bridge.send_groups("node-a"))
            self.assertEqual(("/all/os/groups", ["node-a", 0, 2]),
                             bridge.sender.frames[-1][:2])
            bridge.handle("/os/groups", ["node-a", 0, 2], "127.0.0.1")
            self.assertNotIn("node-a", bridge._group_pending)
            self.assertEqual("current", state.devices["node-a"]["group_sync"]["status"])

            state.devices["node-a"]["online"] = False
            bridge.handle("/os/groups", ["node-a", 0, 2], "127.0.0.1")
            self.assertEqual("offline", state.devices["node-a"]["group_sync"]["status"])
            state.devices["node-a"]["online"] = True

            before = len(bridge.sender.frames)
            bridge.handle("/os/groups", ["node-a", 0], "127.0.0.1")
            self.assertEqual(before + 1, len(bridge.sender.frames))
            record = bridge._group_pending["node-a"]
            before = len(bridge.sender.frames)
            for _ in range(20):
                bridge.handle("/os/groups", ["node-a", 0], "127.0.0.1")
            self.assertIs(record, bridge._group_pending["node-a"])
            self.assertEqual(before, len(bridge.sender.frames))
            self.assertEqual(1, record["attempts"])
            for _ in range(4):
                record.get("timeout") and record["timeout"].cancel()
                bridge._retry_groups("node-a", record)
            self.assertEqual("timeout", state.devices["node-a"]["group_sync"]["status"])
            self.assertNotIn("node-a", bridge._group_pending)

            before = len(bridge.sender.frames)
            bridge.handle("/os/report", [json.dumps({
                "uid": "node-a", "hostname": "a", "groups": [0]})], "10.0.0.1")
            self.assertEqual(before + 1, len(bridge.sender.frames))
            bridge.handle("/os/report", [json.dumps({
                "uid": "node-a", "hostname": "a", "groups": [0, 2]})], "10.0.0.1")
            self.assertEqual("report", state.devices["node-a"]["group_sync"]["source"])
            bridge.close()
            await state.close()

    async def test_reconnect_replay_offline_retention_and_group_param_fanout(self):
        with tempfile.TemporaryDirectory() as directory:
            state, bridge, _events = self.setup_bridge(directory)
            self.assertFalse(bridge.send_groups("node-b"))
            self.assertEqual([0], state.seats["3"]["groups"])
            self.assertTrue(bridge.send_groups("node-a"))
            old_attempt = bridge._group_pending["node-a"]
            old_attempt["timeout"].cancel()
            bridge.sender.frames.clear()
            bridge.handle("/hb", ["node-a", 9, "1.5", 1], "10.0.0.1")
            frames = [(address, args) for address, args, _ in bridge.sender.frames]
            self.assertIn(("/all/os/assign", ["node-a", 1, "Seat 1", 1.0, 1.0]),
                          frames)
            self.assertNotIn(("/all/os/groups", ["node-a", 0, 2]), frames)
            self.assertNotIn("node-a", bridge._group_pending)
            before = len(bridge.sender.frames)
            bridge._retry_groups("node-a", old_attempt)
            self.assertEqual(before, len(bridge.sender.frames))
            state.seats["1"]["groups"] = [2]
            self.assertFalse(bridge.send_groups("node-a"))
            self.assertEqual(before, len(bridge.sender.frames))
            self.assertEqual([2], state.devices["node-a"]["group_sync"]["desired"])
            bridge.handle("/hb", ["node-a", 1, "1.5", 1], "10.0.0.1")
            released = bridge.sender.frames[before:]
            self.assertEqual([("/all/os/groups", ["node-a", 2])],
                             [(address, args) for address, args, _ in released])

            before = len(bridge.sender.frames)
            members = bridge.set_group_param(2, "fx/reverb/gain", .75)
            emitted = bridge.sender.frames[before:]
            self.assertEqual([1, 2], [item["id"] for item in members])
            self.assertEqual(.75, state.seats["1"]["params"]["fx/reverb/gain"])
            self.assertEqual(.75, state.seats["2"]["params"]["fx/reverb/gain"])
            self.assertEqual(.75, state.devices["node-a"]["params"]["fx/reverb/gain"])
            self.assertEqual([("/g2/p/fx/reverb/gain", [.75])],
                             [(address, args) for address, args, _ in emitted])
            bridge.close()
            await state.close()
            reloaded = InstallationState(str(Path(directory) / "installation.json"))
            self.assertEqual(.75, reloaded.seats["2"]["params"]["fx/reverb/gain"])


class FakeOSC:
    def __init__(self, state):
        self.state = state
        self.events = []

    async def unassign(self, uid):
        self.events.append(("unassign", uid))
        return True

    def assign(self, uid, seat_id, _name, _positions):
        self.events.append(("assign", uid, seat_id))

    def send_groups(self, uid):
        seat_state = self.state.seat_for_uid(uid)
        self.events.append(("groups", uid, list(seat_state.get("groups", []))))
        return True


class ServerStateApiTests(unittest.IsolatedAsyncioTestCase):
    def make_dashboard(self, directory):
        dashboard = Dashboard.__new__(Dashboard)
        dashboard.state = InstallationState(str(Path(directory) / "installation.json"))
        dashboard.state.data["supervisor"] = {"mode": "off"}
        dashboard.state.data["editor"] = {"active": False}
        dashboard.supervisor_lock = asyncio.Lock()
        dashboard.osc = FakeOSC(dashboard.state)
        dashboard.messages = []
        dashboard.errors = []

        async def broadcast(this, kind, data):
            this.messages.append((kind, copy.deepcopy(data)))

        async def ws_error(this, _ws, message):
            this.errors.append(message)

        dashboard.broadcast = MethodType(broadcast, dashboard)
        dashboard.ws_error = MethodType(ws_error, dashboard)
        return dashboard

    async def test_state_api_membership_and_bind_transitions(self):
        with tempfile.TemporaryDirectory() as directory:
            dashboard = self.make_dashboard(directory)
            dashboard.state.data["seats"] = {
                "1": seat(1, [], None), "2": seat(2, [], "node-a")}
            dashboard.state.ensure("node-a").update(id=2, online=True, virtual=False)
            await dashboard.handle_ws({"type": "create_group", "data": {"name": "Front"}})
            await dashboard.handle_ws({"type": "set_seat_groups", "data": {
                "id": 1, "groups": [0]}})
            self.assertEqual([0], dashboard.state.seats["1"]["groups"])
            self.assertNotIn(("groups", "node-a", [0]), dashboard.osc.events)

            await dashboard.handle_ws({"type": "bind_seat", "data": {
                "id": 1, "uid": "node-a", "confirmed": True}})
            self.assertEqual([0], dashboard.state.seats["1"]["groups"])
            self.assertIsNone(dashboard.state.seats["2"]["bound"])
            self.assertIn(("assign", "node-a", 1), dashboard.osc.events)
            self.assertNotIn(("groups", "node-a", [0]), dashboard.osc.events)

            await dashboard.handle_ws({"type": "unbind_seat", "data": {"id": 1}})
            self.assertEqual([0], dashboard.state.seats["1"]["groups"])
            self.assertIsNone(dashboard.state.seats["1"]["bound"])
            await dashboard.handle_ws({"type": "delete_group", "data": {"id": 0}})
            self.assertEqual([], dashboard.state.seats["1"]["groups"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
