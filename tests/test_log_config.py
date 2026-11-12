#!/usr/bin/env python3
"""Living tests for log-destination configuration (contract sec 6, v1.13).

Durable shared surface: the bounded internal/usb model, effective resolution
and visible fallback, LOG_DESTINATION persistence, the node's apply/receipt on
the /os/log-config surface, and simfleet parity.
"""

import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
for sub in ("python", "tools"):
    if str(REPO / sub) not in sys.path:
        sys.path.insert(0, str(REPO / sub))

import log_config  # noqa: E402


class LogConfigModuleTest(unittest.TestCase):
    def test_configured_defaults_internal_for_unset_or_bad(self):
        self.assertEqual(log_config.configured({}), "internal")
        self.assertEqual(log_config.configured({"LOG_DESTINATION": ""}), "internal")
        self.assertEqual(log_config.configured({"LOG_DESTINATION": "nope"}), "internal")
        self.assertEqual(log_config.configured({"LOG_DESTINATION": "USB"}), "usb")
        self.assertEqual(log_config.configured({"LOG_DESTINATION": "usb"}), "usb")

    def test_effective_usb_only_when_chosen_and_mounted(self):
        cfg = {"LOG_DESTINATION": "usb"}
        with mock.patch.object(log_config, "usb_present", return_value=True):
            self.assertEqual(log_config.effective(cfg), "usb")
            self.assertEqual(log_config.effective_dir(cfg), log_config.USB_DIR)
        with mock.patch.object(log_config, "usb_present", return_value=False):
            self.assertEqual(log_config.effective(cfg), "internal")
            self.assertEqual(log_config.effective_dir(cfg), log_config.INTERNAL_DIR)

    def test_effective_internal_ignores_usb_presence(self):
        cfg = {"LOG_DESTINATION": "internal"}
        with mock.patch.object(log_config, "usb_present", return_value=True):
            self.assertEqual(log_config.effective(cfg), "internal")

    def test_status_object_shape(self):
        with mock.patch.object(log_config, "usb_present", return_value=False):
            status = log_config.status_object({"LOG_DESTINATION": "usb"})
        self.assertEqual(set(status), {"destination", "effective", "usb_present"})
        self.assertEqual(status, {"destination": "usb", "effective": "internal",
                                  "usb_present": False})

    def test_validate_accepts_only_bounded_destination(self):
        self.assertEqual(log_config.validate({"destination": "internal"}),
                         {"destination": "internal"})
        self.assertEqual(log_config.validate({"destination": "usb"}),
                         {"destination": "usb"})
        for bad in ({}, {"destination": "elsewhere"}, {"destination": "/tmp"},
                    {"destination": "usb", "extra": 1}, [], "usb",
                    {"dest": "usb"}):
            with self.assertRaises(log_config.LogConfigError):
                log_config.validate(bad)

    def test_update_config_file_sets_key_and_preserves_others(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "bopos.config")
            with open(path, "w") as target:
                target.write("SOUNDCARD=DigiAMP\nJACK_SAMPLE_RATE=48000\n")
            log_config.update_config_file(path, "usb")
            text = Path(path).read_text()
            self.assertIn("LOG_DESTINATION=usb", text)
            self.assertIn("SOUNDCARD=DigiAMP", text)
            self.assertIn("JACK_SAMPLE_RATE=48000", text)
            # idempotent replace, not duplicate
            log_config.update_config_file(path, "internal")
            text = Path(path).read_text()
            self.assertEqual(text.count("LOG_DESTINATION="), 1)
            self.assertIn("LOG_DESTINATION=internal", text)

    def test_update_config_file_refuses_invalid(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "bopos.config")
            with self.assertRaises(log_config.LogConfigError):
                log_config.update_config_file(path, "bogus")


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
_ORIGINAL_ARGV = sys.argv
sys.argv = ["bopos.py", "unknown"]
import bopos  # noqa: E402
from store import Store  # noqa: E402
sys.argv = _ORIGINAL_ARGV


class ReplySocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))


class Node:
    def __init__(self, root):
        self.uid = "node-a"
        self.id = 0
        self.version = "abc1234"
        self.update_model = "persistent"
        self.config = {}
        self.store = Store(os.path.join(root, "store"))


class BoposLogConfigApplyTest(unittest.TestCase):
    def test_registered_and_report_carries_log_object(self):
        self.assertIn("/log", bopos.server.handlers)
        with mock.patch.object(log_config, "usb_present", return_value=False):
            report = bopos.log_report(Node(tempfile.mkdtemp()))
        self.assertEqual(set(report), {"destination", "effective", "usb_present"})

    def test_apply_persists_and_replies_ok(self):
        with tempfile.TemporaryDirectory() as root:
            node = Node(root)
            config_path = os.path.join(root, "bopos.config")
            reply = ReplySocket()
            with mock.patch.object(bopos, "BOPOS_DIR", root), \
                    mock.patch.object(log_config, "usb_present", return_value=False):
                ok = bopos.apply_log_config(
                    json.dumps({"destination": "usb"}), reply, "10.0.0.8", node)
            self.assertTrue(ok)
            self.assertIn("LOG_DESTINATION=usb", Path(config_path).read_text())
            self.assertEqual(node.config.get("LOG_DESTINATION"), "usb")
            address, tags, args = (reply.calls[0][0][0], reply.calls[0][0][1],
                                   reply.calls[0][0][2:])
            self.assertEqual(address, "/os/log-config")
            self.assertEqual(args[0], "node-a")
            self.assertEqual(args[1], "ok")
            state = json.loads(args[2])
            self.assertEqual(state["destination"], "usb")
            self.assertEqual(state["effective"], "internal")  # visible fallback

    def test_apply_rejects_invalid_with_err(self):
        with tempfile.TemporaryDirectory() as root:
            node = Node(root)
            reply = ReplySocket()
            with mock.patch.object(bopos, "BOPOS_DIR", root):
                ok = bopos.apply_log_config(
                    json.dumps({"destination": "elsewhere"}), reply, "10.0.0.8", node)
            self.assertFalse(ok)
            self.assertEqual(reply.calls[0][0][2], "node-a")
            self.assertEqual(reply.calls[0][0][3], "err")
            # nothing persisted
            self.assertFalse(os.path.exists(os.path.join(root, "bopos.config")))

    def test_dispatch_routes_log_config_verb(self):
        with tempfile.TemporaryDirectory() as root:
            node = Node(root)
            reply = ReplySocket()
            captured = []
            with mock.patch.object(bopos, "apply_log_config",
                                   lambda *a, **k: captured.append(a)):
                handled = bopos.dispatch_uid_admin(
                    "log-config", [json.dumps({"destination": "usb"})],
                    node, reply, "10.0.0.8")
            self.assertTrue(handled)
            # threaded apply; give it a beat to record the call
            for _ in range(100):
                if captured:
                    break
                threading.Event().wait(0.005)
            self.assertTrue(captured)


class SimfleetLogConfigParityTest(unittest.TestCase):
    def test_uid_admin_log_config_and_effective_fallback(self):
        import simfleet

        device = simfleet.Device("02:00:00:00:00:01", "sim-a", 0, "abc1234")
        # choose usb while absent -> effective internal (visible fallback)
        state = simfleet.device_log_state(device)
        self.assertEqual(state, {"destination": "internal", "effective": "internal",
                                 "usb_present": False})
        device.log_destination = "usb"
        device.usb_present = True
        self.assertEqual(simfleet.device_log_state(device)["effective"], "usb")
        device.usb_present = False
        self.assertEqual(simfleet.device_log_state(device)["effective"], "internal")


if __name__ == "__main__":
    unittest.main()
