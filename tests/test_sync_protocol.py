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
            data = {}
            devices = {uid: {"uid": uid, "ip": "192.0.2.7", "online": True}}
            seat = {"id": 7}

            @staticmethod
            def seat_for_uid(candidate):
                return State.seat if candidate == uid else None

        leader_now = 1_000_000
        bridge = osc_bridge.OSCBridge(State(), lambda *_: None, 15550, 16660,
                                      "255.255.255.255")
        sent, broadcasts = [], []
        bridge._send_to = lambda address, args, destination, route: sent.append((address, args, destination, route))
        bridge.observe_lan_peer = mock.Mock()
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
                ], "192.0.2.7")

        self.assertEqual(sent, [("/7/sync/offset", ["100"], ("192.0.2.7", 16660), "physical")])
        self.assertEqual(bridge.state.devices[uid]["sync"]["offset"], 100)
        self.assertEqual(bridge.state.devices[uid]["sync"]["samples"], 3)
        self.assertTrue(broadcasts)

    def test_unassigned_or_implausibly_late_pong_is_ignored(self):
        uid = "node-a"

        class State:
            data = {}
            devices = {uid: {"uid": uid, "ip": "192.0.2.7", "online": True}}

            @staticmethod
            def seat_for_uid(_candidate):
                return None

        bridge = osc_bridge.OSCBridge(State(), lambda *_: None, 15550, 16660,
                                      "255.255.255.255")
        bridge._send_to = mock.Mock()
        bridge.broadcast = mock.Mock()

        with mock.patch.object(
            osc_bridge.time, "monotonic_ns", return_value=1_000_000
        ):
            bridge.handle_pong([1, "0", uid, "100"], "192.0.2.7")

        self.assertEqual(bridge._sync, {})
        State.seat_for_uid = staticmethod(
            lambda candidate: {"id": 7} if candidate == uid else None
        )
        with mock.patch.object(
            osc_bridge.time,
            "monotonic_ns",
            return_value=osc_bridge.SYNC_RTT_CEILING_NS + 1,
        ):
            bridge.handle_pong([2, "0", uid, "100"], "192.0.2.7")

        self.assertEqual(bridge._sync, {})
        bridge._send_to.assert_not_called()
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


class SyncRoutingTests(unittest.TestCase):
    def setUp(self):
        self.clock = 1_000_000
        self.time_patch = mock.patch.object(osc_bridge.time, "monotonic_ns", side_effect=lambda: self.clock)
        self.time_patch.start()
        self.addCleanup(self.time_patch.stop)
        self.seats = {"a": {"id": 7, "name": "A"}, "b": {"id": 8, "name": "B"}}
        self.state = types.SimpleNamespace(data={}, devices={
            "a": dict(uid="a", ip="192.0.2.7", online=True),
            "b": dict(uid="b", ip="192.0.2.8", online=True)},
            seat_for_uid=lambda uid: self.seats.get(uid))
        self.bridge = osc_bridge.OSCBridge(self.state, mock.Mock(), 15550, 16660,
                                          "255.255.255.255")
        self.bridge._send_to = mock.Mock(return_value=True)
        self.bridge.observe_lan_peer = mock.Mock()

    def pong(self, uid="a", ip=None, stamp=None, device_time=None):
        self.clock += 100
        self.bridge.handle("/sync/pong", [1, str(self.clock-20 if stamp is None else stamp), uid,
            str(self.clock+90 if device_time is None else device_time)],
            ip or self.state.devices[uid]["ip"])

    def settle(self, uid="a"):
        for _ in range(3):
            self.pong(uid)

    def offset_calls(self):
        return [call.args for call in self.bridge._send_to.call_args_list
                if call.args[0].endswith("/sync/offset")]

    def test_source_aware_unicast_uses_lan_selection_and_no_execution_fallback(self):
        self.settle()
        self.assertEqual(self.offset_calls(), [
            ("/7/sync/offset", ["100"], ("192.0.2.7", 16660), "physical")])
        self.bridge.observe_lan_peer.assert_called_once_with("192.0.2.7")
        self.bridge._send_to.return_value = False
        self.pong()
        self.assertTrue(all(call[2][0] == "192.0.2.7" for call in self.offset_calls()))

    def test_duplicate_ip_keeps_uid_windows_and_selectors_independent(self):
        self.state.devices["b"]["ip"] = "192.0.2.7"
        self.settle("a")
        for _ in range(3):
            self.pong("b", device_time=self.clock+290)
        calls = self.offset_calls()
        self.assertEqual([call[0] for call in calls], ["/7/sync/offset", "/8/sync/offset"])
        self.assertTrue(all(call[2] == ("192.0.2.7", 16660) for call in calls))
        self.assertNotEqual(calls[0][1], calls[1][1])

    def test_unknown_unassigned_offline_or_unsafe_peer_never_gets_offset(self):
        for peer in (None, "255.255.255.255", "224.0.0.1", "0.0.0.0", "bad-host"):
            with self.subTest(peer=peer):
                self.state.devices["a"]["ip"] = peer
                self.pong("a", ip="192.0.2.7")
        self.state.devices["a"]["ip"] = "192.0.2.7"
        self.state.devices["a"]["online"] = False
        self.pong()
        self.state.devices["a"]["online"] = True
        self.seats.pop("a")
        self.pong()
        self.pong("unknown", ip="192.0.2.7")
        self.assertEqual(self.offset_calls(), [])

    def test_wrong_source_does_not_change_the_estimate(self):
        self.settle()
        self.pong(ip="192.0.2.99")
        self.assertEqual(self.state.devices["a"]["sync"]["samples"], 3)
        self.assertEqual(len(self.offset_calls()), 1)

    def test_dhcp_change_invalidates_samples_and_old_echo_even_from_new_ip(self):
        self.settle()
        old_stamp = self.clock
        self.state.devices["a"]["ip"] = "192.0.2.70"
        self.pong(ip="192.0.2.7", stamp=old_stamp)
        self.pong(stamp=old_stamp)
        self.assertNotIn("a", self.bridge._sync)
        self.assertNotIn("sync", self.state.devices["a"])
        self.settle()
        self.assertEqual(self.offset_calls()[-1][2], ("192.0.2.70", 16660))
        self.assertEqual(self.state.devices["a"]["sync"]["samples"], 3)

    def test_seat_reindex_and_replacement_start_new_generations(self):
        self.settle()
        old_stamp = self.clock
        self.seats["a"]["id"] = 9
        self.pong(stamp=old_stamp)
        self.assertNotIn("a", self.bridge._sync)
        self.settle()
        self.assertEqual(self.offset_calls()[-1][0], "/9/sync/offset")
        self.seats["a"] = dict(self.seats["a"])
        self.pong(stamp=self.clock)
        self.assertNotIn("a", self.bridge._sync)

    def test_device_replacement_removal_and_offline_invalidate_retained_routes(self):
        self.settle()
        old_device = self.state.devices["a"]
        self.state.devices["a"] = dict(old_device)
        self.pong(stamp=self.clock)
        self.assertNotIn("sync", old_device)
        self.assertNotIn("sync", self.state.devices["a"])
        self.settle()
        self.state.devices["a"]["online"] = False
        self.bridge._refresh_sync_routes()
        self.assertNotIn("a", self.bridge._sync_routes)
        self.assertNotIn("a", self.bridge._sync)
        self.state.devices["a"]["online"] = True
        self.settle()
        del self.state.devices["a"]
        self.bridge._refresh_sync_routes()
        self.assertNotIn("a", self.bridge._sync_routes)
        self.assertNotIn("a", self.bridge._sync_reset_at)

    def test_fast_same_ip_reboot_is_detected_by_backwards_node_clock(self):
        self.settle()
        old_stamp = self.clock
        self.pong(device_time=100)
        self.assertNotIn("a", self.bridge._sync)
        self.pong(stamp=old_stamp)
        self.assertNotIn("a", self.bridge._sync)
        for i in range(3):
            self.pong(device_time=200+i*100)
        self.assertEqual(self.state.devices["a"]["sync"]["samples"], 3)
        self.assertEqual(len(self.offset_calls()), 2)

    def test_heartbeat_ip_change_and_reappearance_clear_generation_before_pongs(self):
        self.state.ensure = lambda uid: self.state.devices[uid]
        self.state.ensure_device_alias = lambda uid: (None, False)
        self.state.save_debounced = mock.Mock()
        self.state.positions_for = lambda selector: []
        self.state.device_enabled_for = lambda uid: True
        for method in ("converge_performance", "send_groups", "set_device_enabled",
                       "request_assets", "request", "assign"):
            setattr(self.bridge, method, mock.Mock())
        for changed_ip, offline in (("192.0.2.70", False), ("192.0.2.70", True)):
            with self.subTest(offline=offline):
                self.settle()
                stamp = self.clock-20
                self.state.devices["a"]["online"] = not offline
                self.bridge.handle("/hb", ["a", 7, "version", 1], changed_ip)
                self.assertNotIn("a", self.bridge._sync)
                self.assertNotIn("sync", self.state.devices["a"])
                self.pong(stamp=stamp)
                self.assertNotIn("a", self.bridge._sync)

    def test_two_virtual_nodes_share_relay_without_sharing_estimates(self):
        self.state.data["supervisor"] = {"mode": "simulate"}
        for device in self.state.devices.values():
            device.update(virtual=True, ip="127.0.0.1")
        self.bridge.set_target("127.0.0.1")
        self.pong(stamp=self.clock-1)  # pre-mode echo, even without an old route
        self.assertNotIn("a", self.bridge._sync)
        self.settle("a")
        self.settle("b")
        self.assertEqual([call[0] for call in self.offset_calls()],
                         ["/7/sync/offset", "/8/sync/offset"])
        self.assertTrue(all(call[2:] == (("127.0.0.1", 16660), "execution")
                            for call in self.offset_calls()))
        self.bridge.observe_lan_peer.assert_not_called()

    def test_reordered_reply_does_not_look_like_a_reboot(self):
        stamp = self.clock
        self.settle()
        self.pong(stamp=stamp, device_time=100)
        self.assertEqual(self.state.devices["a"]["sync"]["samples"], 3)
        self.assertEqual(len(self.offset_calls()), 1)

    def test_assignment_commands_invalidate_old_echoes(self):
        self.settle()
        stamp = self.clock
        self.bridge.uid_command("a", "unassign")
        self.pong(stamp=stamp-1)
        self.assertNotIn("a", self.bridge._sync)
        self.settle()
        self.bridge.assign("a", 7, "Seat")
        self.assertNotIn("a", self.bridge._sync)

    def test_simulation_shared_relay_and_all_mode_transitions_are_isolated(self):
        self.settle()
        self.state.devices["b"].update(virtual=True, ip="127.0.0.1")
        self.state.data["supervisor"] = {"mode": "simulate"}
        self.bridge.set_target("127.0.0.1")
        self.settle("a")  # physical replies are ignored during audition
        self.settle("b")
        self.assertEqual(self.offset_calls()[-1][2:], (("127.0.0.1", 16660), "execution"))
        old_stamp = self.clock
        self.state.data["supervisor"]["mode"] = "edit"
        self.bridge.set_target("127.0.0.1")
        self.pong("b", stamp=old_stamp-1)
        self.assertNotIn("b", self.bridge._sync)
        self.settle("b")
        self.state.data["supervisor"]["mode"] = "off"
        self.bridge.set_target("255.255.255.255")
        self.settle("b")  # virtual replies are ignored in Live
        self.settle("a")
        calls = self.offset_calls()
        self.assertEqual([call[0] for call in calls], ["/7/sync/offset", "/8/sync/offset", "/8/sync/offset", "/7/sync/offset"])
        self.assertTrue(all(call[2][0] != "255.255.255.255" for call in calls))

    def test_patch_editor_endpoint_without_installation_seat_uses_loopback_id_zero(self):
        self.state.data.update(supervisor={"mode": "edit"}, editor={"active": True, "generation": 1})
        self.state.devices["b"].update(virtual=True, editor=True, ip="127.0.0.1")
        self.seats.pop("b")
        self.bridge.set_target("127.0.0.1")
        self.settle("b")
        self.assertEqual(self.offset_calls()[-1],
            ("/0/sync/offset", ["100"], ("127.0.0.1", 16660), "execution"))
        self.state.data["editor"]["generation"] = 2
        self.pong("b", stamp=self.clock)
        self.assertNotIn("b", self.bridge._sync)

    def test_virtual_route_cannot_follow_an_accidental_lan_execution_target(self):
        self.state.data["supervisor"] = {"mode": "simulate"}
        self.state.devices["a"].update(virtual=True, ip="127.0.0.1")
        self.bridge.set_target("192.0.2.123")
        self.settle()
        self.assertEqual(self.offset_calls(), [])


if __name__ == "__main__":
    unittest.main()
