#!/usr/bin/env python3
"""Living tests for attributable node administration outcomes."""

import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "python"), str(REPO / "dashboard")]

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
import osc_bridge  # noqa: E402
sys.argv = ORIGINAL_ARGV


class ReplySocket:
    def __init__(self, events=None):
        self.calls = []
        self.events = events

    def sendto(self, data, target):
        decoded = pyOSC3.decodeOSC(data)
        self.calls.append((decoded, target))
        if self.events is not None:
            self.events.append(("receipt", decoded[2:]))


class AdminOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.state = types.SimpleNamespace(
            uid="node-a",
            update_model="persistent",
            version="old",
        )

    def test_success_and_failure_are_attributable_with_open_ended_phases(self):
        outcomes = (
            ({"status": "ok", "phase": "converged"}, ("ok", "converged")),
            ({"status": "err", "phase": "future-failure"},
             ("err", "future-failure")),
        )
        with mock.patch.object(bopos, "resolve_version", return_value="newsha"):
            for outcome, expected in outcomes:
                reply = ReplySocket()
                with self.subTest(outcome=outcome):
                    bopos.run_admin_verb(
                        lambda *_args, value=outcome: value,
                        [7],
                        self.state,
                        reply,
                        "192.0.2.8",
                    )
                    args = reply.calls[0][0][2:]
                    self.assertEqual(args[:3], [
                        "newsha", "persistent", "node-a",
                    ])
                    self.assertEqual(tuple(args[3:]), expected)
                    self.assertEqual(
                        reply.calls[0][1],
                        ("192.0.2.8", 5550),
                    )

    def test_callback_exception_still_emits_terminal_failure(self):
        def fail(*_args):
            raise RuntimeError("boom")

        reply = ReplySocket()
        with mock.patch.object(
            bopos, "resolve_version", return_value="newsha"
        ):
            bopos.run_admin_verb(
                fail, [], self.state, reply, "192.0.2.8"
            )

        self.assertEqual(reply.calls[0][0][5:], ["err", "exception"])

    def test_reboot_is_requested_after_success_receipt(self):
        events = []
        reply = ReplySocket(events)

        def power(action):
            events.append(("power", action))
            return True

        with (
            mock.patch.object(bopos, "resolve_version", return_value="newsha"),
            mock.patch.object(bopos, "request_power_action", side_effect=power),
        ):
            bopos.run_admin_verb(
                lambda *_args: {
                    "status": "ok", "phase": "converged", "reboot": True,
                },
                [],
                self.state,
                reply,
                "192.0.2.8",
            )

        self.assertEqual(events[0][0], "receipt")
        self.assertEqual(events[0][1][-2:], ["ok", "converged"])
        self.assertEqual(events[1], ("power", "reboot"))

    def test_reboot_rejection_emits_a_second_failure_receipt(self):
        reply = ReplySocket()
        with (
            mock.patch.object(bopos, "resolve_version", return_value="newsha"),
            mock.patch.object(
                bopos, "request_power_action", return_value=False
            ),
        ):
            bopos.run_admin_verb(
                lambda *_args: {
                    "status": "ok", "phase": "converged", "reboot": True,
                },
                [],
                self.state,
                reply,
                "192.0.2.8",
            )

        self.assertEqual(len(reply.calls), 2)
        self.assertEqual(reply.calls[1][0][5:], ["err", "reboot"])

    def test_dashboard_error_receipt_records_outcome_without_refresh_side_effects(self):
        uid = "node-a"
        device = {
            "uid": uid,
            "ip": "192.0.2.8",
            "patch_switch": None,
        }
        state = types.SimpleNamespace(devices={uid: device})
        bridge = object.__new__(osc_bridge.OSCBridge)
        bridge.state = state
        bridge.broadcast = mock.Mock()
        bridge.request = mock.Mock()
        bridge.request_assets = mock.Mock()

        with mock.patch.object(osc_bridge.time, "time", return_value=12.0):
            bridge.handle(
                "/os/rev",
                ["newsha", "persistent", uid, "err", "future-failure",
                 "future-field"],
                "192.0.2.8",
            )

        self.assertEqual(
            device["rev"],
            {
                "sha": "newsha",
                "model": "persistent",
                "status": "err",
                "phase": "future-failure",
                "at": 12.0,
            },
        )
        bridge.broadcast.assert_any_call("rev", device)
        self.assertEqual(
            [call.args[0] for call in bridge.broadcast.call_args_list],
            ["osc_in", "rev"],
        )
        bridge.request.assert_not_called()
        bridge.request_assets.assert_not_called()


if __name__ == "__main__":
    unittest.main()
