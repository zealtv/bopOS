"""Contract amendments and serialized node reports must use one version."""
import json
from pathlib import Path
import re
import sys
import time
from types import SimpleNamespace
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "tools"))

from pythonosc.osc_message import OscMessage
import audition
import simfleet


def documented_version():
    text = (ROOT / "docs/OSC-CONTRACT.md").read_text(encoding="utf-8")
    heading = re.search(r"^\*\*Version (\d+\.\d+)\*\*", text, re.MULTILINE)
    if heading is None:
        raise AssertionError("OSC contract must declare its Version x.y heading")
    return heading.group(1)


class RecordingSocket:
    def __init__(self):
        self.sent = []

    def sendto(self, packet, target):
        self.sent.append((packet, target))


class ContractVersionTests(unittest.TestCase):
    def assert_report_version(self, rig, node):
        rig.sock = RecordingSocket()
        rig.args = SimpleNamespace(report_port=5550)
        rig.started = time.monotonic()
        rig.start_monotonic = rig.started
        rig.send_report(node, ("127.0.0.1", 12345))
        self.assertEqual(len(rig.sock.sent), 1)
        packet, target = rig.sock.sent[0]
        message = OscMessage(packet)
        self.assertEqual(target, ("127.0.0.1", 5550))
        self.assertEqual(message.address, "/os/report")
        self.assertEqual(len(message.params), 1)
        self.assertIsInstance(message.params[0], str)
        self.assertEqual(json.loads(message.params[0])["contract_version"],
                         documented_version())

    def test_shared_version_matches_ratified_contract_heading(self):
        import osc_contract
        self.assertEqual(osc_contract.VERSION, documented_version())

    def test_simfleet_serializes_current_contract_version(self):
        rig = simfleet.SimFleet.__new__(simfleet.SimFleet)
        node = simfleet.Device("node-a", "Node A", 0, "test")
        self.assert_report_version(rig, node)

    def test_audition_serializes_current_contract_version(self):
        rig = audition.AuditionRig.__new__(audition.AuditionRig)
        rig._load_patch = lambda: ("/test/patch", {"engine": "test", "caps": []})
        node = audition.VirtualNode(0, 0, "audition-0001", 7000)
        self.assert_report_version(rig, node)


if __name__ == "__main__":
    unittest.main()
