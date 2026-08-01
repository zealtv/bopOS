#!/usr/bin/env python3
"""Socket-level verify for the v1.14 `/e/*` plane (thread 44 child 3).

Launches the real `tools/simfleet.py` on non-default ports with no engine, then
sends genuine `/<selector>/e/<identity>` datagrams over UDP and asserts what
each simulated node logged. This is the check the delegate could not run — its
sandbox forbids binding UDP — so it is run here, cold, against the shipped
simulator rather than an in-process handler call.

Covers, per the stitch instructions:
  * all three selectors (all / group / seat)
  * arity 0, 1, 2 and 3
  * the `"0"` sentinel firing on arrival
  * a normal lead firing at its deadline, not on arrival

Repo root is found by marker (`tools/simfleet.py`) so the script survives the
`tie` move into `.loom/tied/`.
"""
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

REPORT_PORT = 15561
CMD_PORT = 16661


def repo_root():
    here = Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "tools" / "simfleet.py").exists():
            return candidate
    raise SystemExit("could not locate repo root by marker")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "python"))
from pyOSC3 import OSCMessage  # noqa: E402


def send(address, args):
    msg = OSCMessage(address)
    for value in args:
        msg.append(value, 's' if isinstance(value, str) else 'f')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(msg.getBinary(), ("127.0.0.1", CMD_PORT))
    sock.close()


FIRED = re.compile(r"id=(\d+) event (\S+) fired .*?fire_mono=(\d+)"
                   r"(?: elements=(.*?))?(?: LATE)?$")


def fires(lines):
    """[(device_id, identity, fire_mono_ns, elements_string)] in log order."""
    found = []
    for line in lines:
        match = FIRED.search(line.rstrip())
        if match:
            found.append((int(match.group(1)), match.group(2),
                          int(match.group(3)), (match.group(4) or "").strip()))
    return found


def main():
    log_path = Path(os.environ.get("TMPDIR", "/tmp")) / "verify_event_wire.log"
    log = open(log_path, "w+")
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "tools" / "simfleet.py"),
         "--devices", "3", "--boot-secs", "0",
         "--report-port", str(REPORT_PORT), "--cmd-port", str(CMD_PORT),
         "--target", "127.0.0.1"],
        cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT)
    failures = []
    try:
        time.sleep(2.0)  # let the nodes boot and start heartbeating

        # --- group membership so /g0/e/* has a target -----------------------
        send("/all/os/to", ["", ""])  # no-op; keeps the socket warm
        time.sleep(0.2)

        # --- sentinel: fires on arrival, all selectors, all arities ---------
        mark = time.monotonic_ns()
        send("/all/e/snap", ["0"])                       # arity 0
        send("/1/e/note", ["0", 60.0])                   # arity 1, seat 1
        send("/all/e/pair", ["0", 1.0, 2.0])             # arity 2
        send("/all/e/section/hit", ["0", 1.0, 2.0, 3.0])  # arity 3, nested
        time.sleep(1.0)
        log.flush()
        arrival = fires(Path(log_path).read_text().splitlines())

        by_identity = {}
        for device_id, identity, mono, elements in arrival:
            by_identity.setdefault(identity, []).append(
                (device_id, mono, elements))

        for identity, expected_devices, expected_elements in (
                ("snap", 3, ""),
                ("note", 1, "60"),
                ("pair", 3, "1 2"),
                ("section/hit", 3, "1 2 3")):
            got = by_identity.get(identity, [])
            if len(got) != expected_devices:
                failures.append(
                    f"{identity}: expected {expected_devices} node fires, "
                    f"got {len(got)}")
                continue
            if got[0][2] != expected_elements:
                failures.append(
                    f"{identity}: elements {got[0][2]!r} != "
                    f"{expected_elements!r}")
            if got[0][1] - mark > 900_000_000:
                failures.append(f"{identity}: sentinel did not fire on arrival")

        if by_identity.get("note") and by_identity["note"][0][0] != 1:
            failures.append("seat selector /1/e/note reached the wrong node")

        # --- a normal lead fires at its deadline, not on arrival ------------
        lead_ns = 700_000_000
        before = len(fires(Path(log_path).read_text().splitlines()))
        deadline = time.monotonic_ns() + lead_ns
        sent_at = time.monotonic_ns()
        send("/all/e/later", [str(deadline)])
        time.sleep(0.35)
        log.flush()
        early = fires(Path(log_path).read_text().splitlines())[before:]
        if any(identity == "later" for _d, identity, _m, _e in early):
            failures.append("scheduled event fired early (before its deadline)")
        time.sleep(1.0)
        log.flush()
        late = fires(Path(log_path).read_text().splitlines())[before:]
        later = [f for f in late if f[1] == "later"]
        if len(later) != 3:
            failures.append(
                f"scheduled event: expected 3 node fires, got {len(later)}")
        else:
            elapsed = later[0][2] - sent_at
            if not 0.4e9 <= elapsed <= 1.2e9:
                failures.append(
                    f"scheduled event fired {elapsed/1e6:.0f}ms after send, "
                    "expected ~700ms")

        # --- group selector -------------------------------------------------
        # simfleet nodes start ungrouped, so /g0/e/* must reach nobody; that is
        # the honest assertion available without a dashboard to author groups.
        before = len(fires(Path(log_path).read_text().splitlines()))
        send("/g0/e/snap", ["0"])
        time.sleep(0.6)
        log.flush()
        grouped = fires(Path(log_path).read_text().splitlines())[before:]
        if grouped:
            failures.append(
                f"/g0/e/snap reached {len(grouped)} ungrouped nodes")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()

    if failures:
        print("FAIL")
        for failure in failures:
            print("  -", failure)
        print(f"simfleet log: {log_path}")
        return 1
    print("PASS: /e/* reaches simulated nodes at all/seat selectors, arity 0-3,")
    print("      the \"0\" sentinel fires on arrival, a lead fires at its deadline,")
    print("      and a group selector matching nobody reaches nobody.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
