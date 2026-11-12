#!/usr/bin/env python3
"""Regressions for safe retry generations in dashboard fetch bookkeeping."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

import osc_bridge  # noqa: E402
import server  # noqa: E402


UID = "02:53:49:4d:00:01"
SLOT = "patch:alpha"


class State:
    def __init__(self):
        self.devices = {
            UID: {
                "uid": UID,
                "id": 4,
                "ip": "192.0.2.4",
                "online": True,
                "fetch": {},
                "distribution": {},
            }
        }
        self.data = {}
        self.saved = 0

    def save_debounced(self):
        self.saved += 1


class FetchGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.state = State()
        self.events = []
        self.bridge = osc_bridge.OSCBridge(
            self.state,
            lambda kind, data=None: self.events.append((kind, data)),
            15550,
            16660,
            "192.0.2.255",
        )
        self.bridge.send_physical = mock.Mock()

    async def asyncTearDown(self):
        self.bridge.close()

    async def test_expired_generation_does_not_block_retry_or_certify_it(self):
        with mock.patch.object(osc_bridge, "FETCH_TIMEOUT_SECONDS", 60):
            self.assertTrue(self.bridge.fetch(
                UID, "http://host/old", SLOT, "old-fingerprint"))
            old = self.bridge.fetch_pending[SLOT][0]
            self.bridge._expire_fetch(SLOT, old)

            self.assertFalse(self.bridge.fetch_matches(
                UID, SLOT, "old-fingerprint"))
            self.assertTrue(self.bridge.fetch(
                UID, "http://host/new", SLOT, "new-fingerprint"))
            self.assertEqual(self.bridge.send_physical.call_count, 2)

            # The first terminal after retry is ambiguous. It retires the old
            # tombstone and forces the new bytes to be requested again; it may
            # not certify the new fingerprint.
            self.bridge.handle("/os/fetched", [SLOT, "ok"], "192.0.2.4")
            self.assertEqual(self.bridge.send_physical.call_count, 3)
            self.assertNotIn(SLOT, self.state.devices[UID]["distribution"])
            remaining = list(self.bridge.fetch_pending[SLOT])
            self.assertEqual(len(remaining), 1)
            self.assertEqual(remaining[0]["fingerprint"], "new-fingerprint")

            # Now every possible terminal is for the new bytes, so it is safe
            # to converge the observed distribution fingerprint.
            self.bridge.handle("/os/fetched", [SLOT, "ok"], "192.0.2.4")
            self.assertEqual(
                self.state.devices[UID]["distribution"][SLOT],
                "new-fingerprint",
            )
            self.assertNotIn(SLOT, self.bridge.fetch_pending)

    async def test_live_different_generation_still_blocks_and_never_matches(self):
        with mock.patch.object(osc_bridge, "FETCH_TIMEOUT_SECONDS", 60):
            self.assertTrue(self.bridge.fetch(
                UID, "http://host/old", SLOT, "old-fingerprint"))
            self.assertFalse(self.bridge.fetch(
                UID, "http://host/new", SLOT, "new-fingerprint"))
            self.assertFalse(self.bridge.fetch_matches(
                UID, SLOT, "new-fingerprint"))
            self.assertEqual(self.bridge.send_physical.call_count, 1)

    async def test_live_generation_stranded_by_reboot_does_not_lock_out_retry(self):
        """The reported Finn Jet defect: an acknowledged fetch, then a reboot.

        The node replied `fetching` and then restarted, so no terminal will
        ever arrive. Before the fix this held the slot for the full 1800s
        timeout and `fetch_matches` reported the dead record as in-flight,
        so convergence waited silently and no `/os/fetch` was ever re-sent.
        """
        with mock.patch.object(osc_bridge, "FETCH_TIMEOUT_SECONDS", 1800):
            self.assertTrue(self.bridge.fetch(
                UID, "http://host/bonks", SLOT, "fp"))
            self.bridge.handle("/os/fetch-progress", [SLOT, "queued"], "192.0.2.4")
            self.bridge.handle("/os/fetch-progress", [SLOT, "fetching"], "192.0.2.4")
            self.assertEqual(self.bridge.fetch_pending[SLOT][0]["phase"], "fetching")

            # The dashboard observes the device drop off the network.
            self.bridge.strand_device_fetches(UID)

            self.assertFalse(self.bridge.fetch_matches(UID, SLOT, "fp"))
            self.assertTrue(self.bridge.fetch(UID, "http://host/bonks", SLOT, "fp"))
            self.assertEqual(self.bridge.send_physical.call_count, 2)

    async def test_stalled_generation_is_superseded_without_an_offline_edge(self):
        """A lost terminal with no offline transition still has to recover."""
        with mock.patch.object(osc_bridge, "FETCH_TIMEOUT_SECONDS", 1800), \
                mock.patch.object(osc_bridge, "FETCH_STALL_SECONDS", 120):
            self.assertTrue(self.bridge.fetch(
                UID, "http://host/bonks", SLOT, "fp"))
            self.bridge.handle("/os/fetch-progress", [SLOT, "fetching"], "192.0.2.4")
            record = self.bridge.fetch_pending[SLOT][0]

            # Still progressing: a retry must not disturb it, and the identical
            # generation still coalesces rather than erroring.
            self.assertFalse(self.bridge.fetch(UID, "http://host/bonks", SLOT, "fp"))
            self.assertTrue(self.bridge.fetch_matches(UID, SLOT, "fp"))
            self.assertEqual(self.bridge.send_physical.call_count, 1)

            record["updated_at"] -= 121
            self.assertFalse(self.bridge.fetch_matches(UID, SLOT, "fp"))
            self.assertTrue(self.bridge.fetch(UID, "http://host/bonks", SLOT, "fp"))
            self.assertEqual(self.bridge.send_physical.call_count, 2)

    async def test_progress_refreshes_the_stall_clock(self):
        """A slow multi-file transfer must not be superseded while it reports."""
        with mock.patch.object(osc_bridge, "FETCH_STALL_SECONDS", 120):
            self.bridge.fetch(UID, "http://host/bonks", SLOT, "fp")
            record = self.bridge.fetch_pending[SLOT][0]
            record["updated_at"] -= 121
            self.bridge.handle("/os/fetch-progress", [SLOT, "fetching"], "192.0.2.4")
            self.assertFalse(self.bridge.fetch(UID, "http://host/bonks", SLOT, "fp"))
            self.assertEqual(self.bridge.send_physical.call_count, 1)

    async def test_stranded_generation_still_bars_misattribution(self):
        """Superseding must not weaken the invariant the first pass protected."""
        with mock.patch.object(osc_bridge, "FETCH_TIMEOUT_SECONDS", 1800):
            self.bridge.fetch(UID, "http://host/old", SLOT, "old-fp")
            self.bridge.handle("/os/fetch-progress", [SLOT, "fetching"], "192.0.2.4")
            self.bridge.strand_device_fetches(UID)
            self.bridge.fetch(UID, "http://host/new", SLOT, "new-fp")

            # A late receipt from the stranded generation cannot certify the
            # new bytes; it retires the tombstone and forces a re-send.
            self.bridge.handle("/os/fetched", [SLOT, "ok"], "192.0.2.4")
            self.assertNotIn(SLOT, self.state.devices[UID]["distribution"])
            self.assertEqual(self.bridge.send_physical.call_count, 3)

            self.bridge.handle("/os/fetched", [SLOT, "ok"], "192.0.2.4")
            self.assertEqual(
                self.state.devices[UID]["distribution"][SLOT], "new-fp")


class FetchVisibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_suppressed_fetch_is_broadcast_as_operator_error(self):
        dashboard = server.Dashboard.__new__(server.Dashboard)
        dashboard.fleet_generation = 7
        dashboard.state = SimpleNamespace(devices={
            UID: {"uid": UID, "id": 4, "online": True, "fetch": {}},
        })
        dashboard.device_patch = lambda _uid, _name: None
        dashboard.begin_patch_switch = mock.Mock()
        dashboard.osc = SimpleNamespace(
            fetch=lambda *_args: False,
            fetch_matches=lambda *_args: False,
        )
        broadcasts = []

        async def broadcast(kind, data=None):
            broadcasts.append((kind, data))

        dashboard.broadcast = broadcast
        with mock.patch.object(server, "FETCH_TIMEOUT_SECONDS", 0):
            await dashboard.converge_fleet_patch(
                "alpha",
                "new-fingerprint",
                [UID],
                {UID: "http://host"},
                7,
            )

        errors = [data for kind, data in broadcasts if kind == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("could not start", errors[0]["message"].lower())
        self.assertIn(UID, errors[0]["message"])


if __name__ == "__main__":
    unittest.main()
