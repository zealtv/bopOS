#!/usr/bin/env python3
"""Living Dashboard tests for physical versus execution OSC ownership."""

import asyncio
import os
import sys
import unittest
from pathlib import Path

from pythonosc.osc_message import OscMessage

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "dashboard") not in sys.path:
    sys.path.insert(0, str(REPO / "dashboard"))

from osc_bridge import OSCBridge  # noqa: E402
from server import Dashboard  # noqa: E402


class State:
    def __init__(self):
        self.data = {
            "automation": {}, "muted": False, "master": 0.4,
            "points": {}, "groups": {}, "supervisor": {"mode": "off"},
        }
        self.devices = {
            "physical-1": {
                "uid": "physical-1", "id": 4, "online": True,
                "virtual": False,
            },
            "audition-0001": {
                "uid": "audition-0001", "id": 0, "online": True,
                "virtual": True, "seat_id": 0,
            },
        }
        self.seats = {
            "0": {
                "id": 0, "name": "Seat 0", "bound": "physical-1",
                "positions": [], "params": {}, "groups": [],
            },
        }
        self.device_registry = {
            "physical-1": {"device_enabled": True},
        }

    def public(self):
        return self.data

    def ensure(self, uid):
        return self.devices.setdefault(uid, {
            "uid": uid, "id": -1, "online": False, "virtual": False,
        })

    def ensure_device_alias(self, uid):
        if uid in self.device_registry:
            return self.device_registry[uid], False
        self.device_registry[uid] = {"device_enabled": True}
        return self.device_registry[uid], True

    def clean_seat_id(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    clean_group_id = clean_seat_id

    def seat_for_uid(self, uid):
        return next(
            (seat for seat in self.seats.values()
             if seat.get("bound") == uid), None)

    def save_debounced(self):
        pass

    def save(self):
        pass

    def remove_device_alias(self, uid):
        return self.device_registry.pop(uid, None)

    def alias_for(self, uid):
        return self.device_registry.get(uid, {}).get("alias")

    def device_enabled_for(self, uid):
        return self.device_registry.get(uid, {}).get("device_enabled", True)

    def set_device_enabled(self, uid, value):
        if uid not in self.device_registry or not isinstance(value, bool):
            return False
        self.device_registry[uid]["device_enabled"] = value
        return True


class Sender:
    def __init__(self):
        self.frames = []

    def sendto(self, packet, destination):
        message = OscMessage(packet)
        self.frames.append(
            (message.address, list(message.params), destination))

    def close(self):
        pass


class DeviceControlRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.state = State()
        self.bridge = OSCBridge(
            self.state, lambda *_args: None, 5550, 6660, "192.0.2.255")
        self.sender = Sender()
        self.bridge.sender = self.sender
        # macOS OSC routing (54ff063) may bind a dedicated LAN sender when a
        # physical heartbeat arrives. Keep that real selection path inside the
        # recording fake so this suite does not depend on the host's route to
        # the documentation address used below.
        self.bridge._new_sender = lambda _source=None: self.sender
        self.bridge._source_for_peer = lambda _peer: "192.0.2.1"

    async def asyncTearDown(self):
        for timeout in self.bridge.pending_timeouts.values():
            timeout.cancel()
        for records in self.bridge.fetch_pending.values():
            for record in records:
                record.get("timeout") and record["timeout"].cancel()
        for record in self.bridge._group_pending.values():
            record.get("timeout") and record["timeout"].cancel()
        for timeout in self.bridge._audio_apply_timeouts.values():
            timeout.cancel()

    def assert_destinations(self, destination):
        self.assertTrue(self.sender.frames)
        self.assertTrue(all(
            frame[2] == destination for frame in self.sender.frames),
            self.sender.frames)

    async def test_physical_device_surface_ignores_all_execution_modes(self):
        for mode, target in (
                ("off", "192.0.2.255"),
                ("simulate", "127.0.0.1"),
                ("edit", "127.0.0.1")):
            with self.subTest(mode=mode):
                self.state.data["supervisor"] = {"mode": mode}
                self.bridge.set_target(target)
                self.sender.frames.clear()
                self.bridge.set_device_enabled("physical-1", False)
                self.bridge.set_device_hostname("physical-1", "finn-jet")
                self.bridge.set_audio_config("physical-1", {
                    "card": "DigiAMP", "mixer_control": "Digital",
                    "sample_rate": 44100, "period_size": 512, "nperiods": 2,
                })
                for verb in (
                        "identify", "report", "reboot", "shutdown",
                        "restart-engine", "updatebopos"):
                    self.bridge.uid_action("physical-1", verb)
                self.bridge.assign("physical-1", 0, "Seat 0")
                self.bridge.send_groups("physical-1", [])
                for member in ("params", "patches", "assets"):
                    self.bridge.pending[member].clear()
                    self.bridge.request("physical-1", member)
                self.bridge.os_command(4, "pullpatch")
                self.bridge.os_command(4, "patch", ["alpha"])
                self.bridge.os_command(4, "dropassets", ["drums"])
                self.bridge.fetch(
                    "physical-1", "http://host/manifest", "drums", "sha")
                self.assert_destinations(("192.0.2.255", 6660))

    async def test_execution_controls_follow_all_execution_modes(self):
        for mode, target in (
                ("off", "192.0.2.255"),
                ("simulate", "127.0.0.1"),
                ("edit", "127.0.0.1")):
            with self.subTest(mode=mode):
                self.state.data["supervisor"] = {"mode": mode}
                self.bridge.set_target(target)
                self.sender.frames.clear()
                self.bridge.send_master()
                self.bridge.send_mute_all()
                self.bridge.set_param("all", "gain", 0.5)
                self.bridge.fire_event("all", "go", [], 0)
                self.bridge.send_points_frame()
                self.assert_destinations((target, 6660))

    async def test_patch_edit_accepts_device_enabled_and_mute_all(self):
        dashboard = Dashboard.__new__(Dashboard)
        dashboard.osc = self.bridge
        dashboard.state = self.state
        dashboard.supervisor_lock = asyncio.Lock()
        dashboard.manifest_lock = asyncio.Lock()
        errors = []

        async def broadcast(*_args):
            pass

        async def ws_error(_ws, message):
            errors.append(message)

        dashboard.broadcast = broadcast
        dashboard.ws_error = ws_error
        self.state.data["supervisor"] = {"mode": "edit"}
        self.bridge.set_target("127.0.0.1")
        await dashboard.handle_ws({
            "type": "set_device_enabled",
            "data": {"uid": "physical-1", "value": 0},
        })
        await dashboard.handle_ws({
            "type": "mute_all", "data": {"value": 1},
        })
        self.assertEqual(errors, [])
        self.assertEqual(
            self.sender.frames[-2],
            ("/all/os/to", ["physical-1", "enabled", 0],
             ("192.0.2.255", 6660)))
        self.assertEqual(
            self.sender.frames[-1],
            ("/all/os/mute", [1], ("127.0.0.1", 6660)))

    async def test_execution_restore_emits_no_physical_state(self):
        dashboard = Dashboard.__new__(Dashboard)
        dashboard.osc = self.bridge
        dashboard.state = self.state
        dashboard.performance_target = "192.0.2.255"
        self.bridge.set_target("127.0.0.1")
        self.sender.frames.clear()
        dashboard.restore_live_state()
        self.assertEqual(
            [frame[0] for frame in self.sender.frames],
            ["/all/os/master", "/all/os/mute"])
        self.assertFalse(any(
            frame[0] in ("/all/os/to", "/all/os/assign", "/all/os/groups")
            for frame in self.sender.frames))

    async def test_reappearing_physical_device_replays_persistent_enabled_state(self):
        self.state.device_registry["physical-1"]["device_enabled"] = False
        self.state.devices["physical-1"]["online"] = False
        self.sender.frames.clear()

        self.bridge.handle(
            "/hb", ["physical-1", 0, "abc1234", 1], "192.0.2.4"
        )

        enabled = [
            frame for frame in self.sender.frames
            if frame[0] == "/all/os/to"
            and frame[1][:2] == ["physical-1", "enabled"]
        ]
        self.assertEqual(
            enabled,
            [("/all/os/to", ["physical-1", "enabled", 0],
              ("192.0.2.255", 6660))],
        )

    async def test_forget_is_host_only(self):
        uid = "physical-2"
        self.state.devices[uid] = {
            "uid": uid, "id": -1, "online": False, "virtual": False,
        }
        self.state.device_registry[uid] = {
            "alias": "Niko Cloud", "device_enabled": True,
        }
        dashboard = Dashboard.__new__(Dashboard)
        dashboard.osc = self.bridge
        dashboard.state = self.state
        dashboard.supervisor_lock = asyncio.Lock()
        dashboard.manifest_lock = asyncio.Lock()

        async def broadcast(*_args):
            pass

        async def ws_error(_ws, message):
            self.fail(message)

        dashboard.broadcast = broadcast
        dashboard.ws_error = ws_error
        self.sender.frames.clear()
        await dashboard.handle_ws({
            "type": "forget_device", "data": {"uid": uid},
        })
        self.assertNotIn(uid, self.state.devices)
        self.assertNotIn(uid, self.state.device_registry)
        self.assertEqual(self.sender.frames, [])


if __name__ == "__main__":
    unittest.main()
