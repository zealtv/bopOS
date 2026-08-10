#!/usr/bin/env python3
"""Living regression for supervisor stderr visibility (thread 61/2).

`launch_supervisor` used to pass `stderr=DEVNULL`, so the traceback naming a
missing Pd path -- the whole explanation of 61's originating incident -- was
discarded before anyone could read it. What reached the operator was `running`
followed by `stopped unexpectedly`: the same two words any crash produces, for
any reason.

These tests drive real child processes rather than fakes, because the two
failures worth guarding against are both real-process behaviours: losing the
output, and deadlocking on an undrained pipe.
"""

import asyncio
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

import server as server_module  # noqa: E402
from server import Dashboard  # noqa: E402


def python_child(source):
    return [sys.executable, "-c", source]


class RecordingClient:
    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)


class SupervisorErrorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        # Ports nothing else in the suite binds; the bridge is never driven.
        self.dashboard = Dashboard(Namespace(
            state_file=os.path.join(self.temporary.name, "installation.json"),
            devices_file=os.path.join(self.temporary.name, "devices.json"),
            listen_port=15561, send_port=16671, osc_target="127.0.0.1",
            assets_dir=os.path.join(self.temporary.name, "assets"),
            patches_dir=str(ROOT / "patches"),
        ))
        self.client = RecordingClient()
        self.dashboard.clients.add(self.client)

    async def asyncTearDown(self):
        self.dashboard.osc.close()
        await self.dashboard.state.close()
        self.temporary.cleanup()

    async def run_supervisor(self, source, mode="edit", timeout=20):
        """Launch a child and wait for the exit task the dashboard spawned."""
        launched = await self.dashboard.launch_supervisor(python_child(source), mode)
        self.assertTrue(launched)
        await asyncio.wait_for(
            asyncio.gather(*tuple(self.dashboard.tasks), return_exceptions=True),
            timeout=timeout)

    def broadcasts(self, message_type):
        return [message for message in self.client.messages
                if message.get("type") == message_type]

    async def test_stderr_reaches_the_error_log_and_the_status(self):
        await self.run_supervisor(
            "import sys; sys.stderr.write('PdBinaryError: no usable Pure Data "
            "executable: tried /no/such/pd\\n'); sys.exit(1)")

        errors = self.dashboard.supervisor_errors
        self.assertEqual(len(errors), 1)
        entry = errors[0]
        self.assertEqual(entry["mode"], "edit")
        self.assertEqual(entry["returncode"], 1)
        self.assertIn("/no/such/pd", entry["cause"])
        self.assertIn("/no/such/pd", "\n".join(entry["lines"]))

        broadcast = self.broadcasts("supervisor_error")
        self.assertEqual(len(broadcast), 1)
        self.assertIn("/no/such/pd", broadcast[0]["data"]["cause"])

        status = self.dashboard.state.data["editor"]["status"]
        self.assertTrue(status.startswith("stopped unexpectedly"))
        self.assertIn("/no/such/pd", status)

    async def test_cause_is_the_last_traceback_line_not_the_first(self):
        await self.run_supervisor(
            "raise RuntimeError('the explanatory line')", mode="simulate")

        entry = self.dashboard.supervisor_errors[0]
        self.assertEqual(entry["cause"], "RuntimeError: the explanatory line")
        self.assertIn("Traceback", entry["lines"][0])
        self.assertEqual(self.dashboard.state.data["simulation"]["status"],
                         "stopped unexpectedly: RuntimeError: the explanatory line")

    async def test_a_noisy_child_neither_blocks_nor_keeps_a_transcript(self):
        """The deadlock this stitch could most easily introduce.

        An undrained PIPE blocks the child once the buffer fills -- which would
        present as the editor hanging rather than crashing, worse than the
        silence it replaces. 4000 lines is comfortably past the 64KiB pipe
        buffer; the whole run must still finish, and keep only a tail.
        """
        await self.run_supervisor(
            "import sys\n"
            "for i in range(4000): sys.stderr.write('noise %d %s\\n' % (i, 'x' * 40))\n"
            "sys.stderr.write('the last word\\n')\n"
            "sys.exit(3)", timeout=30)

        entry = self.dashboard.supervisor_errors[0]
        self.assertEqual(entry["returncode"], 3)
        self.assertEqual(entry["cause"], "the last word")
        self.assertLessEqual(len(entry["lines"]), server_module.SUPERVISOR_LOG_LINES)
        self.assertNotIn("noise 0 ", "\n".join(entry["lines"]))

    async def test_a_deliberate_stop_is_not_reported_as_an_error(self):
        launched = await self.dashboard.launch_supervisor(
            python_child("import time; time.sleep(60)"), "edit")
        self.assertTrue(launched)
        await self.dashboard.terminate_supervisor_process()
        await asyncio.wait_for(
            asyncio.gather(*tuple(self.dashboard.tasks), return_exceptions=True),
            timeout=20)

        self.assertEqual(self.dashboard.supervisor_errors, [])
        self.assertEqual(self.broadcasts("supervisor_error"), [])

    async def test_the_error_log_is_bounded(self):
        for index in range(server_module.SUPERVISOR_ERROR_LIMIT + 3):
            await self.run_supervisor(
                f"import sys; sys.stderr.write('failure {index}\\n'); sys.exit(1)")
        errors = self.dashboard.supervisor_errors
        self.assertEqual(len(errors), server_module.SUPERVISOR_ERROR_LIMIT)
        self.assertEqual(errors[-1]["cause"],
                         f"failure {server_module.SUPERVISOR_ERROR_LIMIT + 2}")


class SupervisorCauseTests(unittest.TestCase):
    def test_blank_output_yields_no_cause_rather_than_a_blank_status(self):
        self.assertEqual(server_module.supervisor_cause([]), "")
        self.assertEqual(server_module.supervisor_cause(["   ", ""]), "")

    def test_cause_is_truncated(self):
        long_line = "E" * (server_module.SUPERVISOR_CAUSE_CHARS + 50)
        self.assertEqual(len(server_module.supervisor_cause([long_line])),
                         server_module.SUPERVISOR_CAUSE_CHARS)


class MonitorSurfaceTests(unittest.TestCase):
    """The log is the load-bearing half; pin that the panel renders it."""

    def setUp(self):
        self.monitor = (ROOT / "dashboard" / "static" / "js" / "monitor.js").read_text()

    def test_system_panel_has_a_bounded_supervisor_error_log(self):
        self.assertIn("data-monitor-supervisor-errors", self.monitor)
        self.assertIn("data-monitor-supervisor-error-log", self.monitor)
        self.assertIn('ws.on("supervisor_error"', self.monitor)
        self.assertIn("SUPERVISOR_ERROR_LIMIT", self.monitor)
        self.assertIn("supervisorErrors.shift()", self.monitor)

    def test_the_section_is_hidden_when_empty(self):
        self.assertIn("section.hidden = supervisorErrors.length === 0", self.monitor)


if __name__ == "__main__":
    unittest.main()
