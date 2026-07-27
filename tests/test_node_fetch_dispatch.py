#!/usr/bin/env python3
"""Living regression tests for node-side fetch request dispatch."""

import sys
import types
import unittest
import queue
import os
import tempfile
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
    def __init__(self):
        self.calls = []

    def sendto(self, _data, _target):
        self.calls.append((pyOSC3.decodeOSC(_data), _target))


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

    def test_invalid_slot_replies_terminal_error_without_queueing(self):
        message = pyOSC3.OSCMessage("/5/os/fetch")
        message.append("http://dashboard/assets/escape/.manifest.json", "s")
        message.append("../escape", "s")
        state = types.SimpleNamespace(id=5, groups=())
        reply = ReplySocket()

        with mock.patch.object(bopos, "queue_fetch") as queue_fetch:
            handled = bopos.handle_lan_datagram(
                message.getBinary(),
                ("10.0.0.8", 4000),
                reply,
                state,
            )

        self.assertTrue(handled)
        queue_fetch.assert_not_called()
        self.assertEqual(reply.calls[0][0][0], "/os/fetched")
        self.assertEqual(reply.calls[0][0][2:], ["../escape", "err"])

    def test_identical_requests_coalesce_and_late_joiner_sees_phase(self):
        class DormantWorker:
            def start(self):
                pass

            def is_alive(self):
                return True

        first = ReplySocket()
        second = ReplySocket()
        key = ("file:/source", "patch:stage")
        originals = (
            bopos.fetch_queue,
            bopos.fetch_jobs,
            bopos.fetch_worker,
            bopos.fetch_active_key,
        )
        try:
            bopos.fetch_queue = queue.Queue()
            bopos.fetch_jobs = {}
            bopos.fetch_worker = None
            bopos.fetch_active_key = None
            with mock.patch.object(
                bopos.threading, "Thread", return_value=DormantWorker()
            ):
                bopos.queue_fetch(*key, "10.0.0.8", first)
                bopos.fetch_active_key = key
                bopos.queue_fetch(*key, "10.0.0.9", second)

            self.assertEqual(bopos.fetch_queue.qsize(), 1)
            self.assertEqual(len(bopos.fetch_jobs[key]), 2)
            self.assertEqual(first.calls[0][0][2:], ["patch:stage", "queued"])
            self.assertEqual(second.calls[0][0][2:], ["patch:stage", "fetching"])

            class StateStore:
                def __init__(self):
                    self.values = {}

                def put(self, name, values):
                    self.values[name] = values
                    return True

            state = types.SimpleNamespace(id=5, groups=(), store=StateStore())
            message = pyOSC3.OSCMessage("/5/os/store")
            message.append("during-fetch", "s")
            message.append("still-responsive", "s")
            self.assertTrue(bopos.handle_lan_datagram(
                message.getBinary(),
                ("10.0.0.8", 4000),
                ReplySocket(),
                state,
            ))
            self.assertEqual(
                state.store.values["during-fetch"],
                ["still-responsive"],
            )
        finally:
            (
                bopos.fetch_queue,
                bopos.fetch_jobs,
                bopos.fetch_worker,
                bopos.fetch_active_key,
            ) = originals

    def test_active_patch_converges_and_restarts_before_terminal_success(self):
        class WorkerComplete(Exception):
            pass

        class OneJobQueue:
            def __init__(self, key):
                self.key = key
                self.read = False
                self.completed = 0

            def get(self):
                if self.read:
                    raise WorkerComplete()
                self.read = True
                return self.key

            def task_done(self):
                self.completed += 1

        key = ("file:/source", "patch:live")
        reply = ReplySocket()
        job_queue = OneJobQueue(key)
        events = []

        with tempfile.TemporaryDirectory(prefix="bopos-active-fetch-") as root:
            patch = Path(root) / "patches" / "live"
            patch.mkdir(parents=True)

            def run_command(argv, wait_for_start=False):
                events.append(os.path.basename(argv[1]))
                return 0

            def converge(*_args):
                events.append("converge")
                self.assertEqual(events, ["stop-engine.sh", "converge"])
                return True, "bytes converged"

            with (
                mock.patch.object(bopos, "BOPOS_DIR", root),
                mock.patch.object(bopos, "active_patch_path",
                                  return_value=str(patch)),
                mock.patch.object(bopos, "run_command",
                                  side_effect=run_command),
                mock.patch.object(bopos, "engine_alive", return_value=1),
                mock.patch.object(bopos.fetcher, "fetch",
                                  side_effect=converge),
                mock.patch.object(bopos, "fetch_queue", job_queue),
                mock.patch.object(
                    bopos, "fetch_jobs",
                    {key: [(reply, "10.0.0.8")]},
                ),
                mock.patch.object(bopos, "fetch_active_key", None),
            ):
                with self.assertRaises(WorkerComplete):
                    bopos._fetch_worker_loop()

        self.assertEqual(
            events,
            ["stop-engine.sh", "converge", "start-engine.sh"],
        )
        self.assertEqual(job_queue.completed, 1)
        self.assertEqual(
            [call[0][0] for call in reply.calls],
            ["/os/fetch-progress", "/os/fetched"],
        )
        self.assertEqual(reply.calls[-1][0][2:], ["patch:live", "ok"])

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
