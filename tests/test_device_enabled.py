#!/usr/bin/env python3
from project_fixture import project_path, data_root
"""Living tests for positive physical Device enabled state and wire grammar."""

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
for path in (REPO / "python", REPO / "dashboard"):
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
import device_aliases  # noqa: E402
import osc_contract  # noqa: E402
from state import InstallationState  # noqa: E402
from store import Store  # noqa: E402

sys.argv = ORIGINAL_ARGV


class ReplySocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))


class Node:
    def __init__(self, root, uid):
        self.uid = uid
        self.id = -1
        self.version = "abc1234"
        self.update_model = "persistent"
        self.config = {"AUDIO_CHANNELS": "2", "MIXER_CONTROL": None}
        self.store = Store(os.path.join(root, uid, "store"))
        stored = self.store.get("device_enabled")
        self.device_enabled = bool(stored[0]) if stored else True
        self.mute_all = False
        self.mixer_control = None
        self.muted_via_stop = False
        self.groups = ()
        self.elements = []
        self.reports = {}
        self.reports_lock = threading.Lock()


def packet(address, *args):
    message = pyOSC3.OSCMessage(address)
    for value in args:
        message.append(value)
    return message.getBinary()


class DeviceEnabledTests(unittest.TestCase):
    def test_exact_uid_disable_persists_enforces_and_acknowledges(self):
        with tempfile.TemporaryDirectory() as root:
            first, second = Node(root, "node-a"), Node(root, "node-b")
            first_reply, second_reply = ReplySocket(), ReplySocket()
            with mock.patch.object(bopos, "enforce_mute", return_value=True) as enforce:
                for state, reply in ((first, first_reply), (second, second_reply)):
                    self.assertTrue(bopos.handle_lan_datagram(
                        packet("/all/os/to", "node-b", "enabled", 0),
                        ("10.0.0.8", 4000), reply, state))

            self.assertTrue(first.device_enabled)
            self.assertFalse(second.device_enabled)
            self.assertEqual(second.store.get("device_enabled"), [0])
            self.assertEqual(first_reply.calls, [])
            self.assertEqual(
                second_reply.calls[0][0],
                ["/os/enabled", ",sii", "node-b", 0, 0])
            enforce.assert_called_once_with(True, second)

    def test_mute_all_is_independent_from_device_enabled(self):
        with tempfile.TemporaryDirectory() as root:
            node = Node(root, "node-a")
            reply = ReplySocket()
            enforced = []
            with mock.patch.object(
                    bopos, "enforce_mute",
                    side_effect=lambda value, _state=None:
                    enforced.append(bool(value)) or True):
                self.assertTrue(bopos.set_mute(1, node))
                self.assertTrue(
                    bopos.set_device_enabled(1, reply, "10.0.0.8", node))
                self.assertFalse(bopos.output_enabled(node))
                self.assertTrue(bopos.set_mute(0, node))

            self.assertTrue(node.device_enabled)
            self.assertFalse(node.mute_all)
            self.assertTrue(bopos.output_enabled(node))
            self.assertEqual(
                reply.calls[0][0],
                ["/os/enabled", ",sii", "node-a", 1, 0])
            self.assertEqual(enforced, [True, True, False])

    def test_report_uses_v111_positive_fields(self):
        with tempfile.TemporaryDirectory() as root:
            node = Node(root, "node-a")
            reply = ReplySocket()
            self.assertTrue(bopos.report_reply(reply, "10.0.0.8", node))
            report = json.loads(reply.calls[0][0][2])
            self.assertEqual(report["contract_version"], osc_contract.VERSION)
            self.assertEqual(
                {key: report[key] for key in (
                    "device_enabled", "mute_all", "output_enabled")},
                {"device_enabled": True, "mute_all": False,
                 "output_enabled": True})
            self.assertNotIn("device_muted", report)
            self.assertNotIn("muted", report)

    def test_failed_mute_all_preserves_state_report_and_persisted_device_setting(self):
        for enabled in (False, True):
            for previous_mute in (False, True):
                with self.subTest(enabled=enabled, mute_all=previous_mute), \
                        tempfile.TemporaryDirectory() as root:
                    node, reply = Node(root, "node-a"), ReplySocket()
                    node.device_enabled, node.mute_all = enabled, previous_mute
                    self.assertTrue(node.store.put("device_enabled", [int(enabled)]))
                    before = Path(node.store.path("device_enabled")).read_bytes()
                    with mock.patch.object(bopos, "mute_targets", return_value=[("card", "Digital")]), \
                            mock.patch.object(bopos, "run_command", return_value=1) as command, \
                            mock.patch.object(node.store, "put", wraps=node.store.put) as persist:
                        self.assertFalse(bopos.set_mute(int(not previous_mute), node))
                        persist.assert_not_called()
                    action = "mute" if not enabled or not previous_mute else "unmute"
                    command.assert_called_once_with(
                        ["amixer", "-q", "-c", "card", "sset", "Digital", action])
                    self.assertEqual(node.mute_all, previous_mute)
                    self.assertEqual(Path(node.store.path("device_enabled")).read_bytes(), before)
                    self.assertEqual(reply.calls, [])
                    self.assertTrue(bopos.report_reply(reply, "10.0.0.8", node))
                    report = json.loads(reply.calls[0][0][2])
                    self.assertEqual((report["device_enabled"], report["mute_all"], report["output_enabled"]),
                                     (enabled, previous_mute, enabled and not previous_mute))

    def test_mute_all_applies_mixer_before_state_and_never_persists_overlay(self):
        for enabled in (False, True):
            for previous_mute in (False, True):
                with self.subTest(enabled=enabled, mute_all=previous_mute), \
                        tempfile.TemporaryDirectory() as root:
                    node = Node(root, "node-a")
                    node.device_enabled, node.mute_all = enabled, previous_mute
                    def apply(value, state):
                        self.assertEqual(state.mute_all, previous_mute)
                        self.assertEqual(state.device_enabled, enabled)
                        self.assertEqual(value, not enabled or not previous_mute)
                        return True
                    with mock.patch.object(bopos, "enforce_mute", side_effect=apply), \
                            mock.patch.object(node.store, "put") as persist:
                        self.assertTrue(bopos.set_mute(int(not previous_mute), node))
                        persist.assert_not_called()
                    self.assertEqual(node.mute_all, not previous_mute)
                    self.assertEqual(bopos.output_enabled(node), enabled and previous_mute)

    def test_failed_mute_all_lan_request_emits_no_success_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            node, reply = Node(root, "node-a"), ReplySocket()
            with mock.patch.object(bopos, "enforce_mute", return_value=False):
                self.assertTrue(bopos.handle_lan_datagram(
                    packet("/all/os/mute", 1), ("10.0.0.8", 4000), reply, node))
            self.assertFalse(node.mute_all)
            self.assertTrue(bopos.output_enabled(node))
            self.assertEqual(reply.calls, [])

    def test_failed_mute_preserves_persistence_and_reports_output_enabled(self):
        with tempfile.TemporaryDirectory() as root:
            node, reply = Node(root, "node-a"), ReplySocket()
            self.assertTrue(node.store.put("device_enabled", [1]))
            before = Path(node.store.path("device_enabled")).read_bytes()
            with mock.patch.object(bopos, "mute_targets", return_value=[("card", "Digital")]), \
                    mock.patch.object(bopos, "run_command", return_value=1) as command, \
                    mock.patch.object(node.store, "put", wraps=node.store.put) as persist:
                self.assertFalse(
                    bopos.set_device_enabled(0, reply, "10.0.0.8", node))
                persist.assert_not_called()
            command.assert_called_once_with(["amixer", "-q", "-c", "card", "sset", "Digital", "mute"])
            self.assertEqual(reply.calls, [])
            self.assertEqual(Path(node.store.path("device_enabled")).read_bytes(), before)
            self.assertTrue(Node(root, "node-a").device_enabled)
            self.assertTrue(bopos.report_reply(reply, "10.0.0.8", node))
            report = json.loads(reply.calls[0][0][2])
            self.assertTrue(report["device_enabled"])
            self.assertTrue(report["output_enabled"])

    def test_failed_enforcement_preserves_disabled_and_default_states(self):
        for previous in (None, 0):
            with self.subTest(previous=previous), tempfile.TemporaryDirectory() as root:
                node, reply = Node(root, "node-a"), ReplySocket()
                if previous is not None:
                    self.assertTrue(node.store.put("device_enabled", [previous]))
                    node.device_enabled = bool(previous)
                requested = 0 if previous is None else 1
                with mock.patch.object(bopos, "enforce_mute", return_value=False):
                    self.assertFalse(bopos.set_device_enabled(requested, reply, "10.0.0.8", node))
                self.assertEqual(node.store.get("device_enabled"), [] if previous is None else [previous])
                self.assertEqual(node.device_enabled, previous is None)
                self.assertEqual(reply.calls, [])
                self.assertTrue(bopos.report_reply(reply, "10.0.0.8", node))
                report = json.loads(reply.calls[0][0][2])
                self.assertEqual(report["device_enabled"], previous is None)
                self.assertEqual(report["output_enabled"], previous is None)

    def test_mixer_is_applied_before_live_state_and_persistence_change(self):
        with tempfile.TemporaryDirectory() as root:
            node, reply = Node(root, "node-a"), ReplySocket()
            self.assertTrue(node.store.put("device_enabled", [1]))
            def apply(value, state):
                self.assertTrue(value)
                self.assertTrue(state.device_enabled)
                self.assertEqual(state.store.get("device_enabled"), [1])
                return True
            with mock.patch.object(bopos, "enforce_mute", side_effect=apply):
                self.assertTrue(bopos.set_device_enabled(0, reply, "10.0.0.8", node))
            self.assertFalse(node.device_enabled)
            self.assertEqual(node.store.get("device_enabled"), [0])
            self.assertFalse(Node(root, "node-a").device_enabled)
            self.assertEqual(reply.calls[0][0], ["/os/enabled", ",sii", "node-a", 0, 0])

    def test_persist_failure_still_reports_successful_mixer_operation_without_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            node, reply = Node(root, "node-a"), ReplySocket()
            self.assertTrue(node.store.put("device_enabled", [1]))
            with mock.patch.object(bopos, "enforce_mute", return_value=True), \
                    mock.patch.object(node.store, "put", return_value=False):
                self.assertFalse(bopos.set_device_enabled(0, reply, "10.0.0.8", node))
            self.assertEqual(node.store.get("device_enabled"), [1])
            self.assertEqual(reply.calls, [])
            self.assertTrue(bopos.report_reply(reply, "10.0.0.8", node))
            report = json.loads(reply.calls[0][0][2])
            self.assertFalse(report["device_enabled"])
            self.assertFalse(report["output_enabled"])

    def test_host_registry_migrates_and_saves_canonical_state(self):
        legacy = {
            "node-a": {
                "alias": "Finn Jet", "source": "custom", "generator": 2,
                "device_muted": True,
                "desired_patch": {"name": "retired", "fingerprint": "a" * 64},
            },
        }
        canonical = {
            "node-a": {
                "alias": "Finn Jet", "source": "custom", "generator": 2,
                "device_enabled": False,
            },
        }
        self.assertEqual(device_aliases.clean_registry(legacy), canonical)

        with tempfile.TemporaryDirectory() as root:
            path = str(project_path(root))
            with open(path, "w", encoding="utf-8") as target:
                json.dump({
                    "schema": 1, "name": "migration", "seats": {},
                    "device_registry": legacy,
                }, target)
            InstallationState(data_root(path))
            with open(os.path.join(root, "devices.json"), encoding="utf-8") as source:
                saved = json.load(source)
            self.assertEqual(saved, canonical)

    def test_node_boot_migrates_and_deletes_legacy_key(self):
        with tempfile.TemporaryDirectory() as root:
            store = Store(os.path.join(root, "state", "store"))
            self.assertTrue(store.put("device_muted", [1]))
            with mock.patch.object(bopos, "BOPOS_DIR", root):
                node = bopos.NodeState(["bopos.py", "node-a"])
            self.assertFalse(node.device_enabled)
            self.assertEqual(node.store.get("device_enabled"), [0])
            self.assertEqual(node.store.get("device_muted"), [])

    def test_contract_and_reference_publish_only_the_v111_exact_uid_grammar(self):
        contract = (REPO / "docs" / "OSC-CONTRACT.md").read_text(
            encoding="utf-8")
        reference = (REPO / "docs" / "OSC-REFERENCE.md").read_text(
            encoding="utf-8")
        for document in (contract, reference):
            self.assertIn("/all/os/to <uid", document)
            self.assertIn("enabled <0", document)
            self.assertIn("/os/enabled", document)
            self.assertNotIn("/all/os/to <uid> mute", document)


if __name__ == "__main__":
    unittest.main()
