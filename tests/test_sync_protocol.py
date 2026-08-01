#!/usr/bin/env python3
"""Living tests for sync leader estimation and node event scheduling."""

import sys
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "python"), str(REPO / "dashboard")]

import osc_bridge  # noqa: E402
from sync_node import EventScheduler, SyncState  # noqa: E402


class SyncProtocolTests(unittest.TestCase):
    def test_leader_estimate_prefers_low_rtt_samples_and_uses_their_median(self):
        window = {
            "offsets": [100, 110, 10_000, 90],
            "rtts": [10, 11, 100, 12],
        }
        self.assertEqual(
            osc_bridge.OSCBridge._sync_estimate(window),
            100,
        )

    def test_assigned_device_receives_offset_after_minimum_samples(self):
        uid = "node-a"

        class State:
            devices = {uid: {"uid": uid}}

            @staticmethod
            def seat_for_uid(candidate):
                return {"id": 7} if candidate == uid else None

        leader_now = 1_000_000
        bridge = object.__new__(osc_bridge.OSCBridge)
        bridge.state = State()
        bridge._sync = {}
        bridge._sync_sent = {}
        sent, broadcasts = [], []
        bridge.send = lambda address, args: sent.append((address, args))
        bridge.broadcast = (
            lambda kind, payload=None: broadcasts.append((kind, payload))
        )

        with (
            mock.patch.object(
                osc_bridge.time, "monotonic_ns", return_value=leader_now
            ),
            mock.patch.object(osc_bridge.time, "time", return_value=10.0),
        ):
            for sequence in range(3):
                bridge.handle_pong([
                    sequence,
                    str(leader_now - 20),
                    uid,
                    str(leader_now + 90),
                ])

        self.assertEqual(sent, [("/7/sync/offset", ["100"])])
        self.assertEqual(bridge.state.devices[uid]["sync"]["offset"], 100)
        self.assertEqual(bridge.state.devices[uid]["sync"]["samples"], 3)
        self.assertTrue(broadcasts)

    def test_unassigned_or_implausibly_late_pong_is_ignored(self):
        uid = "node-a"

        class State:
            devices = {uid: {"uid": uid}}

            @staticmethod
            def seat_for_uid(_candidate):
                return None

        bridge = object.__new__(osc_bridge.OSCBridge)
        bridge.state = State()
        bridge._sync = {}
        bridge._sync_sent = {}
        bridge.send = mock.Mock()
        bridge.broadcast = mock.Mock()

        with mock.patch.object(
            osc_bridge.time, "monotonic_ns", return_value=1_000_000
        ):
            bridge.handle_pong([1, "0", uid, "100"])

        self.assertEqual(bridge._sync, {})
        State.seat_for_uid = staticmethod(
            lambda candidate: {"id": 7} if candidate == uid else None
        )
        with mock.patch.object(
            osc_bridge.time,
            "monotonic_ns",
            return_value=osc_bridge.SYNC_RTT_CEILING_NS + 1,
        ):
            bridge.handle_pong([2, "0", uid, "100"])

        self.assertEqual(bridge._sync, {})
        bridge.send.assert_not_called()
        bridge.broadcast.assert_not_called()

    def test_event_scheduler_fires_due_and_grace_events_but_drops_stale(self):
        fired, logs = [], []
        on_time = threading.Event()
        sync = SyncState(slew_ns=0)
        sync.push(0)

        def fire(event_id, elements):
            fired.append((event_id, elements))
            if event_id == "future":
                on_time.set()

        scheduler = EventScheduler(sync, fire=fire, log=logs.append)
        scheduler.start()
        try:
            now = time.monotonic_ns()
            scheduler.schedule(now - 5_000_000, "grace", [])
            scheduler.schedule(now - 100_000_000, "stale", [])
            scheduler.schedule(now + 30_000_000, "future", [])
            self.assertTrue(on_time.wait(0.5))
        finally:
            scheduler.stop()

        self.assertEqual(set(event_id for event_id, _elements in fired),
                         {"grace", "future"})
        self.assertNotIn("stale", [event_id for event_id, _elements in fired])
        self.assertTrue(
            any("stale" in entry and "DROPPED" in entry for entry in logs)
        )

    def test_offset_change_is_continuous_while_events_are_pending(self):
        now = [0]
        sync = SyncState(slew_ns=100, now=lambda: now[0])
        sync.push(100)
        self.assertEqual(sync.offset(), 0)
        now[0] = 50
        self.assertEqual(sync.offset(), 50)
        sync.push(-100)
        self.assertEqual(sync.offset(), 50)
        now[0] = 150
        self.assertEqual(sync.offset(), -100)


if __name__ == "__main__":
    unittest.main()
