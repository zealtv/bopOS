#!/usr/bin/env python3
"""Focused verification for the Dashboard host checkout shorthand."""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True


def repo_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "dashboard" / "server.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "dashboard"))
import server  # noqa: E402


failures = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(label)


expected = subprocess.run(
    ["git", "-C", str(ROOT), "rev-parse", "--short=7", "HEAD"],
    capture_output=True, text=True, check=True).stdout.strip()
actual = server.host_checkout_shorthand(str(ROOT))
check("Dashboard uses Git's seven-character checkout spelling",
      actual == expected and len(actual) == 7, f"expected={expected!r}, actual={actual!r}")

original_run = server.subprocess.run
calls = []
try:
    server.subprocess.run = lambda command, **kwargs: (
        calls.append((command, kwargs))
        or SimpleNamespace(returncode=0, stdout="d9780cc\n"))
    check("Git is explicitly asked for a minimum seven-character abbreviation",
          server.host_checkout_shorthand("/repo") == "d9780cc"
          and calls[0][0] == ["git", "-C", "/repo", "rev-parse", "--short=7", "HEAD"],
          repr(calls))
    server.subprocess.run = lambda _command, **_kwargs: SimpleNamespace(
        returncode=128, stdout="")
    check("startup remains graceful outside a Git checkout",
          server.host_checkout_shorthand("/not-a-repo") is None)
finally:
    server.subprocess.run = original_run

print(f"\n{len(failures)} failure(s)")
raise SystemExit(1 if failures else 0)
