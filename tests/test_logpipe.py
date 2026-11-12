#!/usr/bin/env python3
"""Living tests for the service stdout sink (`python/logpipe.py`).

Durable surface: timestamps, per-boot byte cap, one-generation boot rotation,
and foreground service pipelines that expose failures to systemd.
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
LOGPIPE = REPO / "python" / "logpipe.py"
START_SH = REPO / "bash" / "run" / "service.sh"

# Same shape as nodelog's stamp: 2026-08-14T11:30:01.966+10:00
STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2} ")


def run_pipe(text, path, max_bytes=None):
    argv = [sys.executable, str(LOGPIPE), str(path)]
    if max_bytes is not None:
        argv.append(str(max_bytes))
    subprocess.run(argv, input=text, text=True, check=True, timeout=30)
    return Path(path).read_text()


class LogPipeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "io.log")

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_line_is_timestamped(self):
        body = run_pipe("first\nsecond\n", self.path)
        lines = [line for line in body.splitlines() if line]
        self.assertTrue(lines)
        for line in lines:
            self.assertRegex(line, STAMP_RE)
        self.assertIn("first", body)
        self.assertIn("second", body)

    def test_cap_keeps_the_head_and_reports_the_discards(self):
        # The soak use case: the onset of an error cluster is the diagnosis,
        # so the cap must not be a tail window.
        body = run_pipe("".join("line %d\n" % i for i in range(2000)),
                        self.path, max_bytes=2048)
        self.assertLess(len(body), 2048 + 512, "cap overshoot must stay bounded")
        self.assertIn("line 0", body)
        self.assertNotIn("line 1999", body)
        self.assertIn("size cap reached", body)
        self.assertRegex(body, r"\d+ line\(s\) discarded after the cap")

    def test_uncapped_run_says_so_and_keeps_everything(self):
        body = run_pipe("".join("line %d\n" % i for i in range(500)), self.path)
        self.assertIn("line 499", body)
        self.assertNotIn("size cap reached", body)

    def test_previous_run_is_rotated_once(self):
        run_pipe("older\n", self.path)
        os.utime(self.path, (1, 1))
        sys.path.insert(0, str(REPO / 'python'))
        import logpipe
        with mock.patch.object(logpipe.boot_state, 'boot_time', return_value=100):
            with logpipe.PerformanceSink(self.path) as sink:
                sink.write('newer\n')
        self.assertIn("newer", Path(self.path).read_text())
        self.assertIn("older", Path(self.path + ".prev").read_text())


class StartScriptWiringTest(unittest.TestCase):
    """The redirection is the deliverable; the sink alone changes nothing."""

    def setUp(self):
        self.body = START_SH.read_text()

    def test_both_services_run_unbuffered_through_the_sink(self):
        for service, log in (("python/bopos.py", "bopos.log"),
                             ("python/io/main.py", "io.log")):
            launch = [line for line in self.body.splitlines()
                      if service in line and "PYTHON_BIN" in line]
            self.assertTrue(launch, "no launch line for %s" % service)
            self.assertIn("-u", launch[0], "%s must not block-buffer" % service)
            self.assertIn('log_to "$RUN_DIR/%s"' % log, self.body)

    def test_stderr_is_redirected_too(self):
        # Tracebacks and `Error reading <name>` are the valuable half.
        self.assertEqual(self.body.count("2>&1 |"), 2)

    def test_service_pipeline_exposes_failure_and_keeps_no_pids(self):
        self.assertIn('set -euo pipefail', self.body)
        self.assertNotIn('.pid', self.body)

    def test_current_boot_restarts_append_and_keep_the_cap(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'io.log'
            run_pipe('onset\n', path, 1024)
            for _ in range(8):
                run_pipe('later\n' * 30, path, 1024)
            self.assertIn('onset', path.read_text())
            self.assertLess(path.stat().st_size, 1024 + 4096)
            self.assertFalse(Path(str(path) + '.prev').exists())


if __name__ == "__main__":
    unittest.main()
