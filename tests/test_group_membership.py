#!/usr/bin/env python3
"""Living tests for node group-membership full-state replacement."""

import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "python"))

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
sys.argv = ORIGINAL_ARGV


class Store:
    def __init__(self, values=None, succeeds=True):
        self.values = dict(values or {})
        self.succeeds = succeeds

    def get(self, key):
        return self.values.get(key, [])

    def put(self, key, value):
        if not self.succeeds:
            return False
        self.values[key] = list(value)
        return True


class ReplySocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))


class GroupMembershipTests(unittest.TestCase):
    def state(self, groups=(8,), store=None):
        return types.SimpleNamespace(
            uid="node-a",
            groups=tuple(groups),
            store=store or Store({"groups": list(groups)}),
        )

    def test_exact_uid_replacement_sorts_persists_and_receipts(self):
        state, reply = self.state(), ReplySocket()
        with mock.patch.object(bopos, "send_groups_to_engine") as engine:
            self.assertTrue(
                bopos.apply_groups(
                    ["node-a", 9, 2], reply, "192.0.2.8", state
                )
            )

        self.assertEqual(state.groups, (2, 9))
        self.assertEqual(state.store.values["groups"], [2, 9])
        engine.assert_called_once_with(state)
        self.assertEqual(reply.calls[0][0][0], "/os/groups")
        self.assertEqual(reply.calls[0][0][2:], ["node-a", 2, 9])
        self.assertEqual(reply.calls[0][1], ("192.0.2.8", 5550))

    def test_empty_tail_is_the_complete_clear_state(self):
        state, reply = self.state((2, 9)), ReplySocket()
        with mock.patch.object(bopos, "send_groups_to_engine"):
            self.assertTrue(
                bopos.apply_groups(
                    ["node-a"], reply, "192.0.2.8", state
                )
            )

        self.assertEqual(state.groups, ())
        self.assertEqual(state.store.values["groups"], [])
        self.assertEqual(reply.calls[0][0][2:], ["node-a"])

    def test_uid_mismatch_and_invalid_sets_change_nothing(self):
        for args in (
            ["node-b", 2],
            ["node-a", 2, 2],
            ["node-a", -1],
            ["node-a", "2"],
            ["node-a", 2.0],
        ):
            state, reply = self.state(), ReplySocket()
            with self.subTest(args=args), mock.patch.object(
                bopos, "send_groups_to_engine"
            ) as engine:
                self.assertFalse(
                    bopos.apply_groups(args, reply, "192.0.2.8", state)
                )
                self.assertEqual(state.groups, (8,))
                self.assertEqual(reply.calls, [])
                engine.assert_not_called()

    def test_persistence_failure_exposes_neither_state_nor_receipt(self):
        store = Store({"groups": [8]}, succeeds=False)
        state, reply = self.state(store=store), ReplySocket()
        with mock.patch.object(
            bopos, "send_groups_to_engine"
        ) as engine:
            self.assertFalse(
                bopos.apply_groups(
                    ["node-a", 2, 9], reply, "192.0.2.8", state
                )
            )

        self.assertEqual(state.groups, (8,))
        self.assertEqual(store.values["groups"], [8])
        self.assertEqual(reply.calls, [])
        engine.assert_not_called()


if __name__ == "__main__":
    unittest.main()
