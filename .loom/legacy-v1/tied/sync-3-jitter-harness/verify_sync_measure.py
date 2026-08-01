#!/usr/bin/env python3
"""Verification for sync-3: the clock-sync jitter harness.

Runs tools/sync_measure.py in both modes, hardware-free:
  - sim: launches simfleet, syncs, fires a burst, and must measure the spread
    on every cue across all devices, with per-device offsets that track the
    configured ±skew (proof the harness actually observes cancellation), and a
    spread inside a generous software-floor ceiling;
  - hardware: with no fleet present, must run its sync/fire/print plan and exit
    cleanly (it's a design/one-liner for Bob, not a measurement here).

Deps: pip install python-osc. Run: python3 verify_sync_measure.py
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent

FAILURES = []
FLOOR_CEILING_MS = 10.0  # generous: sim spread is a sub-ms software floor


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def main():
    tool = os.path.join(REPO, "tools/sync_measure.py")
    report = tempfile.NamedTemporaryFile(suffix=".md", delete=False).name
    result = subprocess.run(
        [sys.executable, tool, "--devices", "5", "--sync-skew-ms", "40",
         "--sync-jitter-ms", "2", "--cues", "6", "--settle", "4",
         "--report-port", "15592", "--cmd-port", "16702", "--report", report],
        cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=90)
    print(result.stdout.strip())
    check("sim run exited 0", result.returncode == 0)
    text = open(report).read()

    match = re.search(r"measured (\d+)/(\d+) cues; max spread ([\d.]+) ms", result.stdout)
    check("all cues measured across devices",
          match is not None and match.group(1) == match.group(2),
          result.stdout[-200:])
    if match:
        check("spread within the software-floor ceiling",
              float(match.group(3)) <= FLOOR_CEILING_MS,
              f"{match.group(3)} ms > {FLOOR_CEILING_MS} ms")

    offsets = [float(m) for m in re.findall(r"\| \d+ \| \S+ \| (-?[\d.]+) \|", text)]
    check("an offset estimated for every device", len(offsets) == 5, f"{offsets}")
    # tens-of-ms offsets held while spread stayed sub-ms == real skew cancelled
    check("non-trivial offsets estimated (cancellation observed)",
          offsets and max(abs(o) for o in offsets) > 10.0,
          f"max|offset|={max((abs(o) for o in offsets), default=0):.1f}ms")
    check("report flags the floor caveat", "floor" in text.lower())
    os.unlink(report)

    hardware = subprocess.run(
        [sys.executable, tool, "--mode", "hardware", "--cues", "3", "--settle", "1",
         "--report-port", "15593", "--cmd-port", "16703"],
        cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
    check("hardware mode runs and exits 0 with no fleet", hardware.returncode == 0,
          hardware.stdout[-200:])
    check("hardware mode prints an alignable fire schedule",
          "leader monotonic" in hardware.stdout and re.search(r"m0: \d+", hardware.stdout) is not None)

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("sync-3 jitter-harness checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
