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
