#!/usr/bin/env python3
"""Living tests for the v1.14 targetable event plane."""

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

    def test_normal_event_and_cue_still_schedule(self):
        state = types.SimpleNamespace(id=4, groups=())
        event = pyOSC3.OSCMessage("/4/e/go")
        event.append("1234567890", "s")
        event.append(0.5, "f")
        cue = pyOSC3.OSCMessage("/cue")
        cue.append("legacy-go", "s")
        cue.append("1234567890", "s")
        reply = types.SimpleNamespace(sendto=lambda *_args: None)

        with (
            mock.patch.object(bopos.event_scheduler, "schedule") as schedule_event,
            mock.patch.object(bopos.cue_scheduler, "schedule") as schedule_cue,
        ):
            self.assertTrue(bopos.handle_lan_datagram(
                event.getBinary(), ("192.0.2.1", 4000), reply, state))
            self.assertTrue(bopos.handle_lan_datagram(
                cue.getBinary(), ("192.0.2.1", 4000), reply, state))

        schedule_event.assert_called_once_with(1234567890, "go", [0.5])
        schedule_cue.assert_called_once_with(
            1234567890, "legacy-go", [])

    def test_cue_fire_callback_accepts_the_generalized_payload(self):
        # The scheduler is shared, so it calls `fire(identity, elements)` for
        # a cue too. Mocking `schedule` (as the test above must) cannot see an
        # arity mismatch here -- it would only surface as a TypeError inside
        # the scheduler thread at the deadline, i.e. as a cue that silently
        # never fires. Exercise the real callback instead. Child 4 deletes it.
        frames = []
        with mock.patch.object(
                bopos, "send_to_engine",
                side_effect=lambda message: frames.append(
                    pyOSC3.decodeOSC(message.getBinary()))):
            bopos.fire_cue_to_engine("legacy-go", [])

        self.assertEqual(frames[0][0], "/cue")
        self.assertIn("legacy-go", frames[0])

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

    def test_event_lead_loads_old_key_but_saves_only_new_key(self):
        with tempfile.TemporaryDirectory(prefix="bopos-event-lead-") as root:
            path = Path(root) / "installation.json"
            path.write_text(json.dumps({
                "schema": 1,
                "seats": {},
                "groups": {},
                "cue_lead_ms": 0,
            }))
            state = InstallationState(str(path))

        self.assertEqual(state.data["event_lead_ms"], 0)
        self.assertEqual(state.durable()["event_lead_ms"], 0)
        self.assertNotIn("cue_lead_ms", state.durable())


if __name__ == "__main__":
    unittest.main()
