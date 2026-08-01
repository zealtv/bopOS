#!/usr/bin/env python3
"""Living tests for demand-driven Monitor report probing."""

import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

from osc_bridge import OSCBridge  # noqa: E402


class MonitorProbeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.broadcasts = []
        device = {
            "uid": "device-1", "id": 3, "online": True, "virtual": False,
        }
        self.bridge = OSCBridge(
            SimpleNamespace(devices={"device-1": device}, data={}),
            lambda kind, data=None: self.broadcasts.append((kind, data)),
            15550, 16660, "127.0.0.1")
        self.bridge.send_physical = mock.Mock()

    async def asyncTearDown(self):
        for record in self.bridge.probe_pending.values():
            record["timeout"].cancel()

    async def test_probe_routes_by_assigned_id_and_shapes_typed_reply(self):
        ok, error = self.bridge.probe("device-1", "level")
        self.assertTrue(ok)
        self.assertIsNone(error)
        self.bridge.send_physical.assert_called_once_with("/3/os/probe", ["level"])

        self.bridge.handle("/os/probe", [3, "level", 7, .5, "ok"], "127.0.0.1")
        result = [data for kind, data in self.broadcasts if kind == "probe_result"][-1]
        self.assertTrue(result["ok"])
        self.assertEqual(result["uid"], "device-1")
        self.assertEqual(result["values"], [
            {"type": "i", "value": 7},
            {"type": "f", "value": .5},
            {"type": "s", "value": "ok"},
        ])
        self.assertFalse(self.bridge.probe_pending)

    async def test_unassigned_and_invalid_name_are_rejected(self):
        self.bridge.state.devices["device-1"]["id"] = -1
        self.assertFalse(self.bridge.probe("device-1", "level")[0])
        self.bridge.state.devices["device-1"]["id"] = 3
        self.assertFalse(self.bridge.probe("device-1", "bad name")[0])


if __name__ == "__main__":
    unittest.main()
