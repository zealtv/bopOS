#!/usr/bin/env python3
"""Run the living physical-device control mode-matrix verifier."""

from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True


def repository_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "CLAUDE.md").is_file() and (parent / ".loom").is_dir():
            return parent
    raise RuntimeError("could not locate the bopOS repository root")


runpy.run_path(
    str(repository_root() / "tests" / "verify_device_control_modes.py"),
    run_name="__main__",
)
