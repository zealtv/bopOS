#!/usr/bin/env python3
"""Living tests for the repository-root software test runner."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "tools" / "run-tests.sh"


class TestRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bopos-runner-")
        self.root = Path(self.temp.name)
        self.fake_python = self.root / "fake-python"
        self.fake_python.write_text(
            """#!/bin/sh
printf 'FAKE_ENV=%s FAKE_ARGS=%s\\n' "$PYTHONDONTWRITEBYTECODE" "$*"
if [ "${FAKE_FAIL_FAST:-0}" = 1 ] && [ "${1:-}" = "-m" ]; then
    exit 9
fi
if [ -n "${FAKE_FAIL_NAME:-}" ]; then
    case "$*" in
        *"$FAKE_FAIL_NAME"*) exit 7 ;;
    esac
fi
exit 0
"""
        )
        self.fake_python.chmod(0o755)

    def tearDown(self):
        self.temp.cleanup()

    def run_runner(self, *args, **extra_env):
        environment = dict(
            os.environ,
            BOPOS_PYTHON=str(self.fake_python),
            **extra_env,
        )
        return subprocess.run(
            [str(RUNNER), *args],
            cwd=self.root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_default_is_fast_from_any_working_directory(self):
        result = self.run_runner()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("=== fast: browser-free living suite ===", result.stdout)
        self.assertIn(
            "FAKE_ARGS=-m unittest discover -s tests -p test_*.py",
            result.stdout,
        )
        self.assertIn("FAKE_ENV=1", result.stdout)
        self.assertNotIn(".loom/tied", result.stdout)

    def test_invalid_tier_or_extra_arguments_prints_usage(self):
        for args in (("unknown",), ("fast", "extra")):
            with self.subTest(args=args):
                result = self.run_runner(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIn(
                    "usage: ./tools/run-tests.sh [fast|browser|all]",
                    result.stderr,
                )
                self.assertNotIn("FAKE_ARGS", result.stdout)

    def test_missing_python_reports_setup_guidance(self):
        missing = self.root / "missing-python"
        environment = dict(os.environ, BOPOS_PYTHON=str(missing))
        result = subprocess.run(
            [str(RUNNER), "fast"],
            cwd=self.root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("BOPOS_PYTHON", result.stderr)
        self.assertIn("python3 -m venv ~/.venvs/bopos", result.stderr)

    def test_browser_continues_and_summarizes_every_surface(self):
        verifiers = sorted((REPO / "tests").glob("verify_*.py"))
        self.assertGreater(len(verifiers), 2)
        failed = verifiers[len(verifiers) // 2].name

        result = self.run_runner("browser", FAKE_FAIL_NAME=failed)

        self.assertEqual(result.returncode, 1)
        for verifier in verifiers:
            self.assertIn(f"FAKE_ARGS=tests/{verifier.name}", result.stdout)
        self.assertIn(f"FAIL {failed}", result.stdout)
        self.assertIn(f"PASS {verifiers[-1].name}", result.stdout)
        self.assertLess(
            result.stdout.index(f"FAIL {failed}"),
            result.stdout.index(f"PASS {verifiers[-1].name}"),
        )

    def test_all_runs_browser_after_fast_failure_and_returns_nonzero(self):
        result = self.run_runner("all", FAKE_FAIL_FAST="1")

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "FAKE_ARGS=-m unittest discover -s tests -p test_*.py",
            result.stdout,
        )
        self.assertIn("=== browser summary ===", result.stdout)
        self.assertIn("PASS verify_", result.stdout)


if __name__ == "__main__":
    unittest.main()
