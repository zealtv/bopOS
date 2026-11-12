#!/usr/bin/env python3
"""Living validation tests for typed Monitor OSC sends."""

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

from server import Dashboard  # noqa: E402


class MonitorSendValidationTests(unittest.TestCase):
    def clean(self, address, args):
        return Dashboard.clean_monitor_message({"address": address, "args": args})

    def test_accepts_typed_values(self):
        address, values, error = self.clean("/all/os/ping", [
            {"type": "s", "value": "hello world"},
            {"type": "i", "value": 7},
            {"type": "f", "value": .123456},
        ])
        self.assertIsNone(error)
        self.assertEqual(address, "/all/os/ping")
        self.assertEqual(values, ["hello world", 7, .123456])

    def test_rejects_invalid_address(self):
        _address, _values, error = self.clean("all/os/ping", [])
        self.assertEqual(error, "OSC address is invalid.")

    def test_rejects_overprecision_float(self):
        _address, _values, error = self.clean(
            "/p/gain", [{"type": "f", "value": .1234567}])
        self.assertEqual(error, "OSC float needs at most 6 significant figures.")

    def test_rejects_unknown_type_and_boolean_number(self):
        self.assertIsNotNone(self.clean(
            "/p/gain", [{"type": "d", "value": 1}])[2])
        self.assertIsNotNone(self.clean(
            "/p/gain", [{"type": "i", "value": True}])[2])


if __name__ == "__main__":
    unittest.main()
