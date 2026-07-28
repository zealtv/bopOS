#!/usr/bin/env python3
"""Living tests for the v1.14 targetable event plane."""

import asyncio
import json
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
for path in (REPO / "python", REPO / "dashboard", REPO / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import pyOSC3  # noqa: E402


class FakeServer:
    def __init__(self, _target):
        self.handlers = {}

    def addMsgHandler(self, address, callback):
        self.handlers[address] = callback

    def close(self):
        pass


class FakeClient:
    def connect(self, _target):
        pass

    def send(self, _message):
        pass


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
ORIGINAL_ARGV = sys.argv
sys.argv = ["bopos.py", "unknown"]

import bopos  # noqa: E402
import simfleet  # noqa: E402
from osc_bridge import OSCBridge  # noqa: E402
from server import Dashboard  # noqa: E402
from show_engine import ShowEngine  # noqa: E402
from state import InstallationState  # noqa: E402
from sync_node import EventScheduler, SyncState  # noqa: E402

sys.argv = ORIGINAL_ARGV


class Sender:
    def __init__(self):
        self.frames = []

    def sendto(self, packet, destination):
        self.frames.append(
            (pyOSC3.decodeOSC(packet), destination))

    def close(self):
        pass


class EventPlaneTests(unittest.TestCase):
    def test_show_messages_route_events_to_each_target(self):
        bridge = mock.Mock()
        engine = ShowEngine(bridge, mock.AsyncMock(), event_lead_ms=lambda: 25)
        engine._send_message({
            "address": "/e/notes/on",
            "args": [{"type": "f", "value": 60.0},
                     {"type": "f", "value": 0.75}],
            "target": ["all", "g2"],
        })
        self.assertEqual(
            bridge.fire_event.call_args_list,
            [
                mock.call("all", "notes/on", [60.0, 0.75], lead_ms=25),
                mock.call("g2", "notes/on", [60.0, 0.75], lead_ms=25),
            ],
        )

    def test_websocket_event_commands_use_the_exact_event_contract(self):
        dashboard = Dashboard.__new__(Dashboard)
        dashboard.state = types.SimpleNamespace(
            data={"supervisor": {"mode": "off"}, "event_lead_ms": 500},
            save_debounced=mock.Mock(),
        )
        dashboard.osc = mock.Mock()
        dashboard.osc.fire_event.side_effect = [(1234, 25), (0, 0)]
        broadcasts = []

        async def broadcast(kind, data):
            broadcasts.append((kind, data))

        async def public_state():
            return {"event_lead_ms": dashboard.state.data["event_lead_ms"]}

        dashboard.broadcast = broadcast
        dashboard.public_state = public_state

        async def exercise():
            await dashboard.handle_ws({
                "type": "set_event_lead", "data": {"ms": 12000}})
            await dashboard.handle_ws({
                "type": "fire_event",
                "data": {
                    "selector": "g2", "identity": "notes/on",
                    "elements": [60, 0.75], "lead_ms": 25,
                },
            })
            dashboard.state.data["supervisor"]["mode"] = "edit"
            await dashboard.handle_ws({
                "type": "fire_editor_event",
                # The browser sends no selector: the editor drives the local
                # audition engine, and the server supplies seat 0 itself.
                "data": {"identity": "snap", "elements": [], "lead_ms": 999},
            })

        asyncio.run(exercise())

        self.assertEqual(dashboard.state.data["event_lead_ms"], 10000)
        self.assertEqual(
            dashboard.osc.fire_event.call_args_list,
            [
                mock.call("g2", "notes/on", [60.0, 0.75], 25),
                mock.call("0", "snap", [], 0),
            ],
        )
        self.assertIn(("event_scheduled", {
            "selector": "g2", "identity": "notes/on",
            "elements": [60.0, 0.75], "shared_time_ns": "1234",
            "lead_ms": 25,
        }), broadcasts)
        self.assertIn(("editor_event_fired", {
            "identity": "snap", "shared_time_ns": "0",
        }), broadcasts)

    def test_websocket_event_validation_sends_the_usual_error_frame(self):
        dashboard = Dashboard.__new__(Dashboard)
        dashboard.state = types.SimpleNamespace(
            data={"supervisor": {"mode": "off"}})
        dashboard.osc = mock.Mock()

        class WebSocket:
            def __init__(self):
                self.frames = []

            async def send_json(self, frame):
                self.frames.append(frame)

        ws = WebSocket()
        asyncio.run(dashboard.handle_ws({
            "type": "fire_event",
            "data": {
                "selector": "all", "identity": "bad identity",
                "elements": [1.0, 2.0, 3.0, 4.0], "lead_ms": 25,
            },
        }, ws))
        self.assertEqual(ws.frames[0]["type"], "error")
        dashboard.osc.fire_event.assert_not_called()

    def test_scheduler_fires_identity_and_elements_at_deadline(self):
        fired = []
        ready = threading.Event()
        sync = SyncState(slew_ns=0)
        sync.push(0)

        def fire(identity, elements):
            fired.append((identity, elements, time.monotonic_ns()))
            ready.set()

        scheduler = EventScheduler(sync, fire, log=lambda _entry: None)
        scheduler.start()
        try:
            deadline = time.monotonic_ns() + 30_000_000
            scheduler.schedule(deadline, "notes/on", [60.0, 0.75])
            self.assertTrue(ready.wait(0.5))
        finally:
            scheduler.stop()

        self.assertEqual(fired[0][:2], ("notes/on", [60.0, 0.75]))
        self.assertGreaterEqual(fired[0][2], deadline)

    def test_bridge_round_trips_arity_zero_through_three(self):
        state = types.SimpleNamespace(data={"supervisor": {"mode": "off"}})
        bridge = OSCBridge(
            state, lambda *_args: None, 5550, 6660, "192.0.2.255")
        sender = Sender()
        bridge.sender = sender
        try:
            with mock.patch("osc_bridge.time.monotonic_ns",
                            return_value=1_000_000_000):
                for arity in range(4):
                    elements = [index + 0.25 for index in range(arity)]
                    shared, lead = bridge.fire_event(
                        "g2", "notes/on", elements, 25)
                    self.assertEqual((shared, lead), (1_025_000_000, 25))
        finally:
            bridge.close()

        self.assertEqual(len(sender.frames), 4)
        for arity, (decoded, destination) in enumerate(sender.frames):
            self.assertEqual(decoded[0], "/g2/e/notes/on")
            self.assertEqual(decoded[2], "1025000000")
            self.assertEqual(len(decoded[3:]), arity)
            for actual, expected in zip(
                    decoded[3:], [index + 0.25 for index in range(arity)]):
                self.assertAlmostEqual(actual, expected, places=6)
            self.assertEqual(destination, ("192.0.2.255", 6660))

    def test_zero_sentinel_fires_immediately_for_all_group_and_seat(self):
        state = types.SimpleNamespace(id=4, groups=(2,))
        fired = []
        with mock.patch.object(
                bopos, "fire_event_to_engine",
                side_effect=lambda identity, elements: fired.append(
                    (identity, elements))):
            for selector, arity in zip(("all", "g2", "4"), (0, 1, 3)):
                message = pyOSC3.OSCMessage(
                    f"/{selector}/e/drums/hit")
                message.append("0", "s")
                for index in range(arity):
                    message.append(index + 0.5, "f")
                self.assertTrue(bopos.handle_lan_datagram(
                    message.getBinary(), ("192.0.2.1", 4000),
                    types.SimpleNamespace(sendto=lambda *_args: None), state))

        self.assertEqual([len(elements) for _identity, elements in fired],
                         [0, 1, 3])
        self.assertTrue(all(identity == "drums/hit"
                            for identity, _elements in fired))

    def test_normal_event_schedules_and_retired_plane_is_unhandled(self):
        state = types.SimpleNamespace(id=4, groups=())
        event = pyOSC3.OSCMessage("/4/e/go")
        event.append("1234567890", "s")
        event.append(0.5, "f")
        retired = pyOSC3.OSCMessage("/cue")
        retired.append("legacy-go", "s")
        retired.append("1234567890", "s")
        reply = types.SimpleNamespace(sendto=lambda *_args: None)

        with mock.patch.object(
                bopos.event_scheduler, "schedule") as schedule_event:
            self.assertTrue(bopos.handle_lan_datagram(
                event.getBinary(), ("192.0.2.1", 4000), reply, state))
            self.assertFalse(bopos.handle_lan_datagram(
                retired.getBinary(), ("192.0.2.1", 4000), reply, state))

        schedule_event.assert_called_once_with(1234567890, "go", [0.5])

    def test_engine_fire_is_selector_free_time_free_and_arity_zero_to_three(self):
        frames = []
        with mock.patch.object(
                bopos, "send_to_engine",
                side_effect=lambda message: frames.append(
                    pyOSC3.decodeOSC(message.getBinary()))):
            for arity in range(4):
                bopos.fire_event_to_engine(
                    "notes/on",
                    [0.123456789 + index for index in range(arity)])

        self.assertEqual(len(frames), 4)
        for arity, decoded in enumerate(frames):
            self.assertEqual(decoded[0], "/e/notes/on")
            self.assertEqual(len(decoded[2:]), arity)
        self.assertAlmostEqual(frames[-1][2], 0.123457, places=6)

    def test_bridge_zero_lead_sends_exact_string_sentinel(self):
        state = types.SimpleNamespace(data={"supervisor": {"mode": "off"}})
        bridge = OSCBridge(
            state, lambda *_args: None, 5550, 6660, "192.0.2.255")
        sender = Sender()
        bridge.sender = sender
        try:
            self.assertEqual(
                bridge.fire_event("all", "go", [], 0), (0, 0))
        finally:
            bridge.close()

        decoded, _destination = sender.frames[0]
        self.assertEqual(decoded[0], "/all/e/go")
        self.assertEqual(decoded[2:], ["0"])

    def test_simfleet_selectors_sentinel_and_normal_deadline(self):
        device = types.SimpleNamespace(
            unresponsive=False, state="running", device_id=4, groups=(2,),
            sync_offset_ns=500, sync_skew_ns=0, hostname="node-4")
        fleet = object.__new__(simfleet.SimFleet)
        fleet.args = types.SimpleNamespace(drop=0.0)
        fleet.devices = [device]
        fleet.protocol = simfleet.ContractProtocol()
        logs, scheduled = [], []
        fleet.log = lambda target, message: logs.append((target, message))
        fleet.schedule = (
            lambda delay, callback, *values:
            scheduled.append((delay, callback, values)))

        for selector in ("all", "g2", "4"):
            fleet.handle_event(
                [selector, "e", "nested", "go"], ["0", 0.5])

        self.assertEqual(len(logs), 3)
        self.assertTrue(all("event nested/go fired" in message
                            for _device, message in logs))
        logs.clear()

        shared = time.monotonic_ns() + 50_000_000
        fleet.handle_event(
            ["4", "e", "nested", "go"], [str(shared), 0.5, 1.0])
        self.assertEqual(logs, [])
        self.assertEqual(len(scheduled), 1)
        delay, callback, values = scheduled[0]
        self.assertGreater(delay, 0)
        self.assertEqual(values[3], shared + device.sync_offset_ns)
        callback(*values)
        self.assertIn("event nested/go fired", logs[0][1])

    def test_event_lead_does_not_load_the_retired_key(self):
        with tempfile.TemporaryDirectory(prefix="bopos-event-lead-") as root:
            path = Path(root) / "installation.json"
            path.write_text(json.dumps({
                "schema": 1,
                "seats": {},
                "groups": {},
                "cue_lead_ms": 0,
            }))
            state = InstallationState(str(path))

        self.assertEqual(state.data["event_lead_ms"], 500)
        self.assertEqual(state.durable()["event_lead_ms"], 500)
        self.assertNotIn("cue_lead_ms", state.durable())


if __name__ == "__main__":
    unittest.main()
