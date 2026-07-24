#!/usr/bin/env python3
"""Living tests for the node logging facility (OSC contract sec 4.2 /log).

Durable shared surface (per the 2026-07-23 testing ruling): the append-only
log's stamp format, TSV shape, daily-file naming, invalid-stream drop, and
append-only behaviour across calls -- plus the /log engine handler wiring in
bopos.py and simfleet's /log parity. Not a tied guard.
"""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
for sub in ("python", "tools"):
    if str(REPO / sub) not in sys.path:
        sys.path.insert(0, str(REPO / sub))

import nodelog  # noqa: E402

# ISO-8601 local time, offset, millisecond precision:
# 2026-07-24T14:03:22.512+01:00 (or ...+00:00 / a negative offset).
STAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2}$")


class NodeLogFacilityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.log = nodelog.NodeLog(destination_dir=self.dir)

    def tearDown(self):
        self.log.close()
        self.tmp.cleanup()

    def read_files(self):
        return sorted(os.listdir(self.dir))

    def read_lines(self, name):
        with open(os.path.join(self.dir, name)) as source:
            return source.read().splitlines()

    def test_stamp_format_is_iso8601_local_with_offset_ms(self):
        self.assertTrue(self.log.append("presses", ["1071.5"]))
        self.log.close()
        (name,) = self.read_files()
        (line,) = self.read_lines(name)
        stamp = line.split("\t")[0]
        self.assertRegex(stamp, STAMP_RE)

    def test_tsv_shape_three_fields_values_space_joined(self):
        self.assertTrue(self.log.append("btn", [1, "down", 2.5]))
        self.log.close()
        (name,) = self.read_files()
        (line,) = self.read_lines(name)
        fields = line.split("\t")
        self.assertEqual(len(fields), 3)
        self.assertEqual(fields[1], "btn")
        self.assertEqual(fields[2], "1 down 2.5")

    def test_daily_file_naming(self):
        # File is <stream>-YYYY-MM-DD.log; the date matches the entry stamp.
        self.log.append("presses", [1])
        self.log.close()
        (name,) = self.read_files()
        self.assertTrue(
            re.fullmatch(r"presses-\d{4}-\d{2}-\d{2}\.log", name), name)
        (line,) = self.read_lines(name)
        stamp_date = line.split("\t")[0][:10]
        self.assertTrue(name.startswith("presses-" + stamp_date))

    def test_invalid_stream_dropped_no_file(self):
        for bad in ["", "has space", "dots.not.allowed", "slash/x", "../esc"]:
            self.assertFalse(self.log.append(bad, [1]), bad)
        self.assertEqual(self.read_files(), [])

    def test_append_only_across_calls(self):
        self.log.append("s", [1])
        self.log.append("s", [2])
        self.log.append("s", [3])
        self.log.close()
        (name,) = self.read_files()
        lines = self.read_lines(name)
        self.assertEqual(len(lines), 3)
        self.assertEqual([ln.split("\t")[2] for ln in lines], ["1", "2", "3"])

    def test_streams_are_separate_files(self):
        self.log.append("a", [1])
        self.log.append("b", [2])
        self.log.close()
        names = self.read_files()
        self.assertEqual(len(names), 2)
        self.assertTrue(any(n.startswith("a-") for n in names))
        self.assertTrue(any(n.startswith("b-") for n in names))

    def test_empty_values_still_stamps(self):
        self.assertTrue(self.log.append("mark", []))
        self.log.close()
        (name,) = self.read_files()
        (line,) = self.read_lines(name)
        fields = line.split("\t")
        self.assertRegex(fields[0], STAMP_RE)
        self.assertEqual(fields[1], "mark")
        self.assertEqual(fields[2], "")

    def test_file_cap_rolls_to_continuation(self):
        original = nodelog.MAX_FILE_BYTES
        nodelog.MAX_FILE_BYTES = 40  # force a roll after a couple of lines
        try:
            for _ in range(6):
                self.log.append("cap", ["xxxxxxxx"])
            self.log.close()
        finally:
            nodelog.MAX_FILE_BYTES = original
        names = self.read_files()
        # a base daily file plus at least one -N continuation
        self.assertTrue(any(re.fullmatch(r"cap-\d{4}-\d{2}-\d{2}\.log", n)
                            for n in names), names)
        self.assertTrue(any(re.fullmatch(r"cap-\d{4}-\d{2}-\d{2}-\d+\.log", n)
                            for n in names), names)

    def test_destination_hook_reevaluated_per_entry(self):
        # The stitch-4 seam: a callable destination is resolved on every
        # append, so a hot USB switch takes effect without a restart.
        current = {"dir": os.path.join(self.dir, "one")}
        log = nodelog.NodeLog(destination_dir=lambda: current["dir"])
        log.append("s", [1])
        current["dir"] = os.path.join(self.dir, "two")
        log.append("s", [2])
        log.close()
        self.assertTrue(os.path.isdir(os.path.join(self.dir, "one")))
        self.assertTrue(os.path.isdir(os.path.join(self.dir, "two")))

    def test_never_raises_on_unwritable_destination(self):
        # A bad destination is logged and dropped, never raised at the caller.
        log = nodelog.NodeLog(destination_dir="/proc/nonexistent-bopos-logs")
        self.assertFalse(log.append("s", [1]))
        log.close()


class BoposLogHandlerTest(unittest.TestCase):
    """The /log handler is registered on 7770 and calls nodelog.append."""

    def test_log_callback_registered_and_appends(self):
        import types
        from unittest import mock

        # Import bopos.py behind fake pyOSC3 sockets (same shim the other
        # living tests use), so registration is observable and no real UDP
        # socket is bound.
        import pyOSC3

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

        original_server, original_client = pyOSC3.OSCServer, pyOSC3.OSCClient
        original_argv = sys.argv
        pyOSC3.OSCServer, pyOSC3.OSCClient = FakeServer, FakeClient
        sys.argv = ["bopos.py", "unknown"]
        try:
            if "bopos" in sys.modules:
                del sys.modules["bopos"]
            import bopos  # noqa: F401
        finally:
            pyOSC3.OSCServer, pyOSC3.OSCClient = original_server, original_client
            sys.argv = original_argv

        self.assertIn("/log", bopos.server.handlers)

        appended = []
        with mock.patch.object(nodelog, "append",
                               lambda stream, values: appended.append((stream, values))):
            bopos.log_callback(args=["presses", 1071.5])
            bopos.log_callback(args=[])  # missing stream -> no append, no raise
        self.assertEqual(appended, [("presses", [1071.5])])


class SimfleetLogParityTest(unittest.TestCase):
    def test_log_request_records_and_validates(self):
        import simfleet

        device = simfleet.Device("02:00:00:00:00:01", "sim-a", 0, "abc1234")
        fleet = simfleet.SimFleet.__new__(simfleet.SimFleet)
        fleet.log = lambda dev, message: None  # silence sim console output

        simfleet.SimFleet.log_request(fleet, device, "presses", [1071.5])
        simfleet.SimFleet.log_request(fleet, device, "presses", [2000])
        simfleet.SimFleet.log_request(fleet, device, "bad name", [1])  # dropped

        self.assertIn("presses", device.log_streams)
        self.assertEqual(len(device.log_streams["presses"]), 2)
        self.assertEqual([entry[1] for entry in device.log_streams["presses"]],
                         [[1071.5], [2000]])
        self.assertNotIn("bad name", device.log_streams)


if __name__ == "__main__":
    unittest.main()
