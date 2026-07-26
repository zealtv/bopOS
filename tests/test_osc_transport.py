#!/usr/bin/env python3
"""Living regressions for Dashboard OSC routing and shutdown containment."""

import asyncio
import errno
import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "dashboard"))

from osc_bridge import OSCBridge  # noqa: E402
from server import Dashboard  # noqa: E402
from state import InstallationState  # noqa: E402


class RecordingSender:
    def __init__(self, failure=None):
        self.failure = failure
        self.frames = []
        self.closed = False

    def sendto(self, packet, destination):
        if self.failure is not None:
            raise self.failure
        self.frames.append((packet, destination))

    def close(self):
        self.closed = True


class OscTransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.state = InstallationState(
            os.path.join(self.temporary.name, "installation.json"))
        self.events = []
        self.bridge = OSCBridge(
            self.state,
            lambda kind, data: self.events.append((kind, data)),
            listen_port=15550,
            send_port=16660,
            target="255.255.255.255",
        )

    async def asyncTearDown(self):
        self.bridge.close()
        await self.state.close()
        self.temporary.cleanup()

    async def test_errno_49_does_not_truncate_first_heartbeat(self):
        failure = OSError(errno.EADDRNOTAVAIL, "Can't assign requested address")
        failing = RecordingSender(failure)
        self.bridge._source_for_peer = lambda _peer: "192.0.2.100"
        self.bridge._new_sender = lambda _source=None: failing

        uid = "b8:27:eb:b4:64:79"
        self.bridge.handle("/hb", [uid, -1, "dbb1bf3", 1, -41], "192.0.2.103")
        self.bridge.send_physical("/all/os/to", [uid, "report"])

        device = self.state.devices[uid]
        self.assertTrue(device["online"])
        self.assertEqual(device["ip"], "192.0.2.103")
        self.assertEqual(device["version"], "dbb1bf3")
        self.assertEqual(device["engine_alive"], 1)
        self.assertIn(uid, self.state.device_registry)
        kinds = [kind for kind, _data in self.events]
        self.assertIn("heartbeat", kinds)
        self.assertIn("device_update", kinds)
        self.assertIn("state", kinds)
        errors = [data for kind, data in self.events
                  if kind == "osc_transport_error"]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["errno"], errno.EADDRNOTAVAIL)
        self.assertEqual(errors[0]["destination"], "255.255.255.255")
        self.assertNotIn("osc_out", kinds)

    async def test_destination_selects_lan_or_loopback_sender(self):
        loopback = RecordingSender()
        lan = RecordingSender()
        self.bridge.sender = loopback
        self.bridge.lan_sender = lan

        self.bridge.send_physical("/all/os/to", ["physical", "report"])
        self.bridge.set_target("127.0.0.1")
        self.bridge.send("/all/os/master", [0.5])

        self.assertEqual(
            [destination for _packet, destination in lan.frames],
            [("255.255.255.255", 16660)],
        )
        self.assertEqual(
            [destination for _packet, destination in loopback.frames],
            [("127.0.0.1", 16660)],
        )

    async def test_peer_discovery_is_cached_and_failure_rebinds_for_later_send(self):
        sources = iter(("192.0.2.100", "198.51.100.100"))
        probes = []
        senders = {}

        def discover(peer):
            probes.append(peer)
            return next(sources)

        def sender_for(source=None):
            sender = RecordingSender(
                OSError(errno.EADDRNOTAVAIL, "route changed")
                if source == "192.0.2.100" else None)
            senders[source] = sender
            return sender

        self.bridge._source_for_peer = discover
        self.bridge._new_sender = sender_for
        self.bridge.observe_lan_peer("192.0.2.103")
        self.bridge.observe_lan_peer("192.0.2.103")
        self.assertEqual(probes, ["192.0.2.103"])

        self.bridge.send_physical("/all/os/to", ["physical", "report"])
        self.assertEqual(self.bridge.lan_source, "198.51.100.100")
        self.assertEqual(len(senders["198.51.100.100"].frames), 0)

        self.bridge.send_physical("/all/os/to", ["physical", "report"])
        self.assertEqual(
            [destination for _packet, destination
             in senders["198.51.100.100"].frames],
            [("255.255.255.255", 16660)],
        )

    async def test_source_probe_prefers_the_directly_attached_interface(self):
        probe = mock.MagicMock()
        probe.__enter__.return_value = probe
        probe.getsockname.return_value = ("192.0.2.100", 54321)

        with mock.patch("osc_bridge.socket.socket", return_value=probe):
            source = self.bridge._source_for_peer("192.0.2.103")

        self.assertEqual(source, "192.0.2.100")
        probe.setsockopt.assert_called_once_with(
            socket.SOL_SOCKET, socket.SO_DONTROUTE, 1)
        probe.connect.assert_called_once_with(("192.0.2.103", 9))

    async def test_source_probe_falls_back_for_a_routed_venue(self):
        direct = mock.MagicMock()
        direct.__enter__.return_value = direct
        direct.connect.side_effect = OSError(errno.ENETUNREACH, "not directly attached")
        routed = mock.MagicMock()
        routed.__enter__.return_value = routed
        routed.getsockname.return_value = ("198.51.100.100", 54321)

        with mock.patch(
                "osc_bridge.socket.socket", side_effect=(direct, routed)):
            source = self.bridge._source_for_peer("203.0.113.10")

        self.assertEqual(source, "198.51.100.100")
        routed.connect.assert_called_once_with(("203.0.113.10", 9))


class DashboardShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def test_shutdown_runs_every_cleanup_stage_after_failures(self):
        dashboard = Dashboard.__new__(Dashboard)
        sleeper = asyncio.create_task(asyncio.sleep(60))
        dashboard.tasks = {sleeper}
        calls = []

        async def failing_supervisor():
            calls.append("supervisor")
            raise OSError(errno.EADDRNOTAVAIL, "send failed")

        class Osc:
            def close(self):
                calls.append("osc")
                raise OSError("close failed")

        class State:
            async def close(self):
                calls.append("state")

        dashboard.stop_supervisor = failing_supervisor
        dashboard.osc = Osc()
        dashboard.state = State()

        await dashboard.stop()

        self.assertTrue(sleeper.cancelled())
        self.assertEqual(calls, ["supervisor", "osc", "state"])

    async def test_already_off_supervisor_emits_no_osc(self):
        dashboard = Dashboard.__new__(Dashboard)
        dashboard.state = type(
            "State", (), {"data": {"supervisor": {"mode": "off"}}})()
        dashboard.sim_process = None
        dashboard.supervisor_generation = 0
        calls = []

        async def terminate():
            calls.append("terminate")

        dashboard.terminate_supervisor_process = terminate
        dashboard.clear_audition_devices = lambda: calls.append("clear")
        dashboard.restore_live_state = lambda: calls.append("restore")

        await dashboard.stop_supervisor()

        self.assertEqual(calls, ["terminate", "clear"])


class MonitorTransportLogTests(unittest.TestCase):
    def test_system_panel_has_bounded_transport_error_log(self):
        monitor = (REPO / "dashboard" / "static" / "js" / "monitor.js").read_text()
        style = (REPO / "dashboard" / "static" / "css" / "style.css").read_text()

        self.assertIn('ws.on("osc_transport_error"', monitor)
        self.assertIn("TRANSPORT_ERROR_LIMIT = 50", monitor)
        self.assertIn("data-monitor-transport-error-log", monitor)
        self.assertIn('role="log" aria-live="polite"', monitor)
        self.assertIn(".monitor-system-error-log", style)


if __name__ == "__main__":
    unittest.main()
