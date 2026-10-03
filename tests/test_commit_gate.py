"""Exercise the versioned gate through real Git commits in an isolated repo."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class CommitGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bopos-commit-gate-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Git exports repository/index paths while running hooks. Nested test
        # repos must not inherit those paths during the real pre-commit run.
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith("GIT_")}
        self.env["BOPOS_PYTHON"] = sys.executable
        for relative in ("tools/run-tests.sh", "tools/install-hooks.sh",
                         "tools/hooks/pre-commit"):
            dest = self.root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / relative, dest)
        (self.root / "tests").mkdir()
        self.run_cmd("git", "init", "--quiet", check=True)
        self.run_cmd("git", "config", "user.name", "Gate test", check=True)
        self.run_cmd("git", "config", "user.email", "gate@example.invalid", check=True)
        self.run_cmd("./tools/install-hooks.sh", check=True)

    def run_cmd(self, *args, check=False):
        return subprocess.run(args, cwd=self.root, env=self.env,
                              capture_output=True, text=True, check=check)

    def commit_test(self, passes):
        (self.root / "tests/test_example.py").write_text(
            "import unittest\nclass Example(unittest.TestCase):\n"
            f"    def test_example(self): self.assertTrue({passes!r})\n")
        self.run_cmd("git", "add", ".", check=True)
        return self.run_cmd("git", "commit", "-m", "Exercise gate")

    def test_failing_fast_test_refuses_commit_and_retry_passes(self):
        result = self.commit_test(False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("COMMIT REFUSED", result.stderr)
        self.assertIn("FAILED (failures=1)", result.stderr)
        self.assertNotEqual(self.run_cmd("git", "rev-parse", "HEAD").returncode, 0)
        result = self.commit_test(True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("running fast tests", result.stdout + result.stderr)
        self.assertEqual(self.run_cmd("git", "rev-parse", "HEAD").returncode, 0)

    def test_missing_python_refuses_commit(self):
        self.env["BOPOS_PYTHON"] = str(self.root / "missing-python")
        result = self.commit_test(True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("COMMIT REFUSED", result.stderr)
        self.assertIn("Set BOPOS_PYTHON", result.stderr)

    def test_install_is_idempotent_and_preserves_other_hooks_path(self):
        result = self.run_cmd("./tools/install-hooks.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.run_cmd("git", "config", "core.hooksPath", "other-hooks", check=True)
        result = self.run_cmd("./tools/install-hooks.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already points to", result.stderr)
        self.assertEqual(self.run_cmd("git", "config", "--get", "core.hooksPath")
                         .stdout.strip(), "other-hooks")

    def test_install_preserves_existing_default_hook(self):
        self.run_cmd("git", "config", "--unset", "core.hooksPath", check=True)
        hook = self.root / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nexit 0\n")
        hook.chmod(0o755)
        result = self.run_cmd("./tools/install-hooks.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("existing pre-commit hook", result.stderr)


if __name__ == "__main__":
    unittest.main()
