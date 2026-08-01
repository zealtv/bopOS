#!/usr/bin/env python3
"""Verification for sync-1: the dashboard as clock leader.

Real dashboard/server.py + real simfleet (devices given known fake skews), no
browser -- the leader estimator is server-side and observable over the /ws
websocket. Because leader and sim share Linux's system-wide CLOCK_MONOTONIC, a
correct estimate equals the device's fake skew (offset === deviceClock -
leaderClock). simfleet logs each skew; the estimate is read from the "sync" ws
broadcasts and must converge to it.

Checks:
  1. the leader estimates every assigned device's offset and it converges to
     the configured skew within tolerance, despite injected pong jitter;
  2. rtt / min_rtt / samples are surfaced (runtime-only) in the ws state;
  3. regression -- with the ping loop running, a set_param round-trips and
     meter broadcasts still flow, and the server logs no traceback.

Deps: pip install fastapi uvicorn[standard] python-osc websockets
Run:  python3 verify_sync_leader.py
"""
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import time

import websockets

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent

HTTP_PORT = 18092
REPORT_PORT = 15581
CMD_PORT = 16691
SKEW_MS = 30.0
JITTER_MS = 2.0
TOLERANCE_NS = 10_000_000   # estimate must land within 10 ms of the true skew

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


async def collect(ws, seconds, latest, meters, updates):
    """Drain ws for `seconds`, recording latest sync per uid and any meter /
    device_update traffic (regression signal)."""
    deadline = time.monotonic() + seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except asyncio.TimeoutError:
            return
        message = json.loads(raw)
        kind, data = message.get("type"), message.get("data", {})
        if kind == "sync":
            latest[data["uid"]] = data
        elif kind == "meter":
            meters.append(data)
        elif kind == "device_update":
            updates.append(data)


async def main():
    skew_log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    server_log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    state_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    fleet = subprocess.Popen([
        sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "3",
        "--protocol", "v1", "--target", "127.0.0.1",
        "--report-port", str(REPORT_PORT), "--cmd-port", str(CMD_PORT),
        "--hb-interval", "1.0", "--boot-secs", "1.0",
        "--sync-skew-ms", str(SKEW_MS), "--sync-jitter-ms", str(JITTER_MS),
    ], cwd=REPO, stdout=skew_log, stderr=subprocess.STDOUT)
    server = subprocess.Popen([
        sys.executable, os.path.join(REPO, "dashboard/server.py"), "--port", str(HTTP_PORT),
        "--listen-port", str(REPORT_PORT), "--send-port", str(CMD_PORT),
        "--osc-target", "127.0.0.1", "--state-file", state_file,
    ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
    try:
        await asyncio.sleep(9)  # boot + ~14 ping rounds to fill the window

        true_skew = {}   # device id -> configured skew ns
        skew_log.flush()
        with open(skew_log.name) as source:
            for line in source:
                m = re.search(r"id=(\d+).*sync_skew=(-?\d+)ns", line)
                if m:
                    true_skew[int(m.group(1))] = int(m.group(2))
        check("simfleet logged a skew per device", len(true_skew) == 3,
              f"skews={true_skew}")

        latest, meters, updates = {}, [], []
        async with websockets.connect(f"ws://127.0.0.1:{HTTP_PORT}/ws") as ws:
            state = json.loads(await ws.recv())
            uid_to_id = {uid: int(dev["id"])
                         for uid, dev in state["data"]["devices"].items()}
            await collect(ws, 3.0, latest, meters, updates)

            check("leader estimated every assigned device",
                  len([u for u in latest if uid_to_id.get(u, -1) >= 0]) == 3,
                  f"got {sorted(latest)}")
            worst = 0
            for uid, sync in latest.items():
                device_id = uid_to_id.get(uid, -1)
                if device_id < 0 or device_id not in true_skew:
                    continue
                error = abs(int(sync["offset"]) - true_skew[device_id])
                worst = max(worst, error)
                check(f"id={device_id} estimate converged",
                      error <= TOLERANCE_NS,
                      f"est={sync['offset']} skew={true_skew[device_id]} "
                      f"err={error/1e6:.1f}ms")
            check("all estimates within tolerance", worst <= TOLERANCE_NS,
                  f"worst={worst/1e6:.1f}ms")
            some = next(iter(latest.values()), {})
            check("rtt/min_rtt/samples surfaced",
                  all(key in some for key in ("rtt", "min_rtt", "samples")),
                  f"keys={sorted(some)}")

            # regression: non-sync paths still work with the ping loop running
            target = next(uid for uid, i in uid_to_id.items() if i >= 0)
            await ws.send(json.dumps({"type": "set_param",
                                      "data": {"uid": target, "name": "gain", "value": 0.5}}))
            updates.clear()
            await collect(ws, 2.0, latest, meters, updates)
            check("set_param round-trips (server not wedged by sync)",
                  any(u.get("uid") == target
                      and abs(float(u.get("params", {}).get("gain", -9)) - 0.5) < 1e-6
                      for u in updates),
                  f"updates={[u.get('uid') for u in updates]}")
            check("meter broadcasts still flow", len(meters) > 0)
    finally:
        for process in (server, fleet):
            if process.poll() is None:
                process.terminate()
        for process in (server, fleet):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    server_log.flush()
    with open(server_log.name) as source:
        log_text = source.read()
    check("server logged no traceback", "Traceback" not in log_text,
          log_text[-400:])
    for path in (skew_log.name, server_log.name, state_file):
        try:
            os.unlink(path)
        except OSError:
            pass

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("sync-1 leader checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
