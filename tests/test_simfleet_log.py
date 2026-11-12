"""Simfleet log lines stay whole when generator threads log at once.

Each simulated device's param generator ticks on its own thread. Browser
journeys parse the shared log (`p/mode=<value>`), so a line spliced into the
next one's timestamp reads as a bogus value (`p/mode=0` + `10:45:12 ...` ->
`010`). This failed the first CI browser run on 2026-10-03.
"""

import contextlib
import io
import re
import sys
import threading
import time
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "python"), str(ROOT / "tools")]

import simfleet  # noqa: E402


class SlowStream(io.StringIO):
    """Yields inside every write, so unguarded writers interleave reliably."""

    def write(self, text):
        time.sleep(0.0005)
        return super().write(text)


class SimfleetLogTests(unittest.TestCase):
    def test_concurrent_log_lines_are_never_spliced(self):
        fleet = simfleet.SimFleet.__new__(simfleet.SimFleet)
        fleet.tty = False
        devices = [simfleet.Device(f"02:00:00:00:00:0{n}", f"sim-{n}", n, "abc1234")
                   for n in range(1, 4)]
        stream = SlowStream()

        def tick(device):
            for value in range(40):
                simfleet.SimFleet.log(fleet, device, f"p/mode={value % 3}")

        with contextlib.redirect_stdout(stream):
            threads = [threading.Thread(target=tick, args=(device,))
                       for device in devices]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        line = re.compile(r"^\d\d:\d\d:\d\d sim-\d id=\d p/mode=[012]$")
        lines = stream.getvalue().splitlines()
        self.assertEqual(len(lines), 3 * 40)
        self.assertEqual([text for text in lines if not line.match(text)], [])


if __name__ == "__main__":
    unittest.main()
