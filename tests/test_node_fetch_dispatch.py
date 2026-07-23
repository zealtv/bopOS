#!/usr/bin/env python3
"""Living regression tests for node-side fetch request dispatch."""

import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
PYTHON = REPO / "python"
if str(PYTHON) not in sys.path:
    sys.path.insert(0, str(PYTHON))

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


class ReplySocket:
    def sendto(self, _data, _target):
        pass


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
ORIGINAL_ARGV = sys.argv
sys.argv = ["bopos.py", "unknown"]

import bopos  # noqa: E402

sys.argv = ORIGINAL_ARGV


class NodeFetchDispatchTests(unittest.TestCase):
    def test_asset_slot_fetch_reaches_queue(self):
        message = pyOSC3.OSCMessage("/5/os/fetch")
        message.append("http://dashboard/assets/drums/.manifest.json", "s")
        message.append("drums", "s")
        state = types.SimpleNamespace(id=5, groups=())

        with mock.patch.object(bopos, "queue_fetch") as queue_fetch:
            handled = bopos.handle_lan_datagram(
                message.getBinary(),
                ("10.0.0.8", 4000),
                ReplySocket(),
                state,
            )

        self.assertTrue(handled)
        queue_fetch.assert_called_once_with(
            "http://dashboard/assets/drums/.manifest.json",
            "drums",
            "10.0.0.8",
            mock.ANY,
        )

    def test_assignment_does_not_mutate_the_device_hostname(self):
        class Store:
            def __init__(self):
                self.values = {}

            def put(self, key, value):
                self.values[key] = value
                return True

        state = types.SimpleNamespace(
            uid="node-a",
            id=-1,
            groups=(),
            store=Store(),
            elements=[],
        )

        with (
            mock.patch.object(bopos, "send_groups_to_engine"),
            mock.patch.object(bopos, "send_to_engine"),
            mock.patch.object(bopos.os, "system") as shell,
            mock.patch.object(bopos.subprocess, "run") as process,
        ):
            handled = bopos.apply_assign(
                ["node-a", 0, "Seat 0", 1.0, 2.0],
                state,
            )

        self.assertTrue(handled)
        self.assertEqual(state.store.values["assignment"], [0, "Seat 0", 1.0, 2.0])
        shell.assert_not_called()
        process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
