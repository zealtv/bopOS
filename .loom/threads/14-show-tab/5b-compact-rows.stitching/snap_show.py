#!/usr/bin/env python3
"""Screenshot the Show tab against the seeded fixture (before/after artifact)."""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location(
    "verify_show_compact", HERE / "verify_show_compact.py")
module = importlib.util.module_from_spec(spec)
sys.modules["verify_show_compact"] = module
spec.loader.exec_module(module)

if __name__ == "__main__":
    out = HERE / (sys.argv[1] if len(sys.argv) > 1 else "show-tab.png")
    raise SystemExit(module.main(screenshot_only=str(out)))
