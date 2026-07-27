"""Durable simulator parity tests for per-device fetch serialization."""

import heapq
import itertools
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "python"), str(ROOT / "tools")]

from pythonosc import osc_message  # noqa: E402
import simfleet  # noqa: E402


class CaptureSocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        message = osc_message.OscMessage(data)
        self.calls.append((message.address, list(message.params), target))


class SimfleetFetchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bopos-simfetch-")
        self.fleet = object.__new__(simfleet.SimFleet)
        self.fleet.args = types.SimpleNamespace(
            fetch_seconds=0.9,
            report_port=5550,
        )
        self.fleet.assets_dir = self.temp.name
        self.fleet.events = []
        self.fleet.fetch_jobs = {}
        self.fleet.fetch_active = {}
        self.fleet.fetch_pending = {}
        self.fleet.sequence = itertools.count()
        self.fleet.sock = CaptureSocket()
        self.first = simfleet.Device(
            "02:00:00:00:00:01", "sim1", 1, "abc1234"
        )
        self.second = simfleet.Device(
            "02:00:00:00:00:02", "sim2", 2, "abc1234"
        )
        self.first.state = self.second.state = "running"

    def tearDown(self):
        self.temp.cleanup()

    def run_events(self):
        while self.fleet.events:
            _when, _sequence, callback, values = heapq.heappop(
                self.fleet.events
            )
            callback(*values)

    def phases(self, slot):
        return [
            (address, args[1])
            for address, args, _target in self.fleet.sock.calls
            if args and args[0] == slot
            and address in ("/os/fetch-progress", "/os/fetched")
        ]

    def test_distinct_jobs_serialize_per_device_but_devices_are_independent(self):
        source = ("10.0.0.8", 4000)
        self.fleet.queue_fetch(self.first, source, "file:/one", "one")
        self.fleet.queue_fetch(self.first, source, "file:/two", "two")
        self.fleet.queue_fetch(self.second, source, "file:/three", "three")

        first_key = (self.first.mac, "file:/one", "one")
        second_key = (self.first.mac, "file:/two", "two")
        other_key = (self.second.mac, "file:/three", "three")
        self.assertEqual(self.fleet.fetch_active[self.first.mac], first_key)
        self.assertEqual(self.fleet.fetch_pending[self.first.mac], [second_key])
        self.assertEqual(self.fleet.fetch_active[self.second.mac], other_key)

        for job in self.fleet.fetch_jobs.values():
            job["ok"] = False
        self.run_events()

        self.assertEqual(
            self.phases("one"),
            [("/os/fetch-progress", "queued"),
             ("/os/fetch-progress", "fetching"),
             ("/os/fetched", "err")],
        )
        self.assertEqual(
            self.phases("two"),
            [("/os/fetch-progress", "queued"),
             ("/os/fetch-progress", "fetching"),
             ("/os/fetched", "err")],
        )
        self.assertEqual(
            self.phases("three"),
            [("/os/fetch-progress", "queued"),
             ("/os/fetch-progress", "fetching"),
             ("/os/fetched", "err")],
        )

        wire = [
            (address, args[0], args[1])
            for address, args, _target in self.fleet.sock.calls
            if address in ("/os/fetch-progress", "/os/fetched")
        ]
        one_terminal = wire.index(("/os/fetched", "one", "err"))
        two_fetching = wire.index(("/os/fetch-progress", "two", "fetching"))
        self.assertLess(one_terminal, two_fetching)

    def test_identical_inflight_requester_joins_current_phase(self):
        first_source = ("10.0.0.8", 4000)
        late_source = ("10.0.0.9", 4000)
        self.fleet.queue_fetch(self.first, first_source, "file:/same", "same")
        key = (self.first.mac, "file:/same", "same")

        _when, _sequence, callback, values = heapq.heappop(self.fleet.events)
        callback(*values)
        self.assertEqual(self.fleet.fetch_jobs[key]["phase"], "fetching")

        self.fleet.queue_fetch(
            self.first, late_source, "file:/same", "same"
        )
        self.assertEqual(len(self.fleet.fetch_jobs[key]["requesters"]), 2)
        self.assertEqual(
            self.fleet.sock.calls[-1],
            ("/os/fetch-progress", ["same", "fetching"], ("10.0.0.9", 5550)),
        )


if __name__ == "__main__":
    unittest.main()
