#!/usr/bin/env python3
"""Living tests for audition's execution-owned output gate."""

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import audition  # noqa: E402


class AuditionOutputGateTests(unittest.TestCase):
    def setUp(self):
        self.rig = object.__new__(audition.AuditionRig)
        self.rig.nodes = [
            audition.VirtualNode(0, 0, "audition-0001", 16661),
            audition.VirtualNode(1, 1, "audition-0002", 16662),
        ]
        self.rig.param_declarations = {}
        self.sent = []
        self.rig.send_engine = lambda node, address, args=(): self.sent.append(
            (node.uid, address, list(args)))

    def relay(self, address, *args):
        self.rig.relay(audition.osc_datagram(address, *args),
                       ("127.0.0.1", 4000))

    def test_mute_all_sends_zero_and_resume_restores_latest_master(self):
        self.relay("/all/os/master", .6)
        self.assertEqual(
            self.sent,
            [
                ("audition-0001", "/os/master", [.6]),
                ("audition-0002", "/os/master", [.6]),
            ])

        self.sent.clear()
        self.relay("/all/os/mute", 1)
        self.assertEqual(
            self.sent,
            [
                ("audition-0001", "/os/master", [0.0]),
                ("audition-0002", "/os/master", [0.0]),
            ])
        self.assertTrue(all(node.mute_all for node in self.rig.nodes))

        self.sent.clear()
        self.relay("/all/os/master", .25)
        self.assertEqual(
            self.sent,
            [
                ("audition-0001", "/os/master", [0.0]),
                ("audition-0002", "/os/master", [0.0]),
            ])
        self.assertEqual([node.master for node in self.rig.nodes], [.25, .25])

        self.sent.clear()
        self.relay("/all/os/mute", 0)
        self.assertEqual(
            self.sent,
            [
                ("audition-0001", "/os/master", [.25]),
                ("audition-0002", "/os/master", [.25]),
            ])
        self.assertFalse(any(node.mute_all for node in self.rig.nodes))

    def test_selector_only_changes_matching_virtual_node(self):
        self.relay("/1/os/master", .4)
        self.relay("/1/os/mute", 1)

        self.assertEqual(self.rig.nodes[0].master, 1.0)
        self.assertFalse(self.rig.nodes[0].mute_all)
        self.assertEqual(self.rig.nodes[1].master, .4)
        self.assertTrue(self.rig.nodes[1].mute_all)
        self.assertEqual(
            self.sent,
            [
                ("audition-0002", "/os/master", [.4]),
                ("audition-0002", "/os/master", [0.0]),
            ])
        self.assertFalse(any(address == "/os/mute"
                             for _uid, address, _args in self.sent))


if __name__ == "__main__":
    unittest.main()
