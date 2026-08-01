#!/usr/bin/env python3
"""Focused static guard for the removed Monitor traffic-count copy."""

import sys
from pathlib import Path

sys.dont_write_bytecode = True


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "tools" / "simfleet.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


source = (repo_root() / "dashboard/static/js/monitor.js").read_text()
checks = {
    "old count output is absent": "data-monitor-tab-count" not in source,
    "shown label is absent": " shown" not in source.lower(),
    "seen label is absent": " seen" not in source.lower(),
    "traffic rendering remains": "visibleLines.join" in source,
    "bounded visible slice remains": "lines.slice(-CONSOLE_VISIBLE)" in source,
}

failed = []
for label, passed in checks.items():
    print(f"[{'PASS' if passed else 'FAIL'}] {label}")
    if not passed:
        failed.append(label)

print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
raise SystemExit(1 if failed else 0)
