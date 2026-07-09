#!/usr/bin/env python3
"""Verification for spatial-0: the dashboard-side spatial automation engine.

Real dashboard/server.py + real simfleet, no browser -- the engine is
server-side and its output is the per-device /p/gain the dashboard puts on the
wire, which simfleet applies and (spatial-0) logs. The verify assigns three
sim devices to known floor positions, drives the spatial layer over the /ws
websocket the way the facilitator UI (spatial-1) will, and reads the applied
gains back out of simfleet's log.

Checks:
  1. static exactness -- for a point parked at several positions, each device's
     applied gain equals falloff(distance) exactly (linear curve, radius 4 m),
     composed as stored(1.0) x master(1.0) x spatial;
  2. compose with master -- with master 0.5 the applied gain halves (stored x
     master x spatial, the single gain-resolution point);
  3. dynamic envelope -- a point swept along the device line makes each device's
     gain rise to ~1.0 then fall, and the peaks arrive in spatial order (the
     nearer device peaks first);
  4. restore -- deactivating spatial returns every device to stored x master;
  5. regression -- set_param still round-trips and the server logs no traceback.

Deps: pip install fastapi uvicorn[standard] python-osc websockets
Run:  python3 verify_spatial_engine.py
"""
import asyncio
import json
import math
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

HTTP_PORT = 18094
REPORT_PORT = 15583
CMD_PORT = 16693
RADIUS = 4.0
TOL = 0.01

# id -> floor position (metres); a horizontal line so a left->right sweep passes
# each in turn. Expected gains use a linear falloff for exact arithmetic.
LAYOUT = {1: ("dev-a", [2.0, 4.0]), 2: ("dev-b", [5.0, 4.0]), 3: ("dev-c", [8.0, 4.0])}

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def expected(point, position, radius=RADIUS):
    """Linear falloff(distance) -- mirrors spatial._linear for cross-checking."""
    distance = math.hypot(position[0] - point[0], position[1] - point[1])
    return max(0.0, 1.0 - distance / radius)


def read_gains(log_path):
    """Last applied /p/gain per device id from simfleet's log."""
    latest = {}
    with open(log_path) as source:
        for line in source:
            match = re.search(r"id=(\d+) .*p/gain=([-+\d.eE]+)", line)
            if match:
                latest[int(match.group(1))] = float(match.group(2))
    return latest


def sweep_series(log_path):
    """Ordered [(sequence, id, gain)] of every applied /p/gain, for envelopes."""
    series = []
    with open(log_path) as source:
        for order, line in enumerate(source):
            match = re.search(r"id=(\d+) .*p/gain=([-+\d.eE]+)", line)
            if match:
                series.append((order, int(match.group(1)), float(match.group(2))))
    return series


async def send(ws, kind, data):
    await ws.send(json.dumps({"type": kind, "data": data}))


async def drain(ws, seconds, updates=None):
    deadline = time.monotonic() + seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except asyncio.TimeoutError:
            return
        if updates is not None:
            message = json.loads(raw)
            if message.get("type") == "device_update":
                updates.append(message["data"])


async def set_point(ws, log_path, x, y, falloff="linear"):
    """Park the point at (x, y), let the frame land, return applied gains."""
    await send(ws, "set_spatial", {"active": True, "radius": RADIUS,
                                    "falloff": falloff,
                                    "motion": {"type": "static", "point": [x, y]}})
    await drain(ws, 0.7)
    return read_gains(log_path)


async def main():
    sim_log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    server_log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    state_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    fleet = subprocess.Popen([
        sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "3",
        "--protocol", "v1", "--target", "127.0.0.1",
        "--report-port", str(REPORT_PORT), "--cmd-port", str(CMD_PORT),
        "--hb-interval", "1.0", "--boot-secs", "1.0",
    ], cwd=REPO, stdout=sim_log, stderr=subprocess.STDOUT)
    server = subprocess.Popen([
        sys.executable, os.path.join(REPO, "dashboard/server.py"), "--port", str(HTTP_PORT),
        "--listen-port", str(REPORT_PORT), "--send-port", str(CMD_PORT),
        "--osc-target", "127.0.0.1", "--state-file", state_file,
    ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
    try:
        await asyncio.sleep(4)  # boot + a couple heartbeats so all 3 are known

        async with websockets.connect(f"ws://127.0.0.1:{HTTP_PORT}/ws") as ws:
            state = json.loads(await ws.recv())
            seen = set(state["data"]["devices"])
            # collect stragglers from heartbeat/device_update if the snapshot
            # was taken before all three announced
            deadline = time.monotonic() + 5
            while len(seen) < 3 and time.monotonic() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                message = json.loads(raw)
                data = message.get("data", {})
                if message.get("type") in ("device_update", "heartbeat") and data.get("uid"):
                    seen.add(data["uid"])
            uids = sorted(seen)
            check("three sim devices present", len(uids) >= 3, f"uids={uids}")
            uids = uids[:3]

            # assign each to an id + name + floor position, then request the
            # param manifest so the volume param ('gain') is declared
            for uid, device_id in zip(uids, LAYOUT):
                name, pos = LAYOUT[device_id]
                await send(ws, "assign_device", {"uid": uid, "id": device_id, "name": name})
                await drain(ws, 0.2)
                await send(ws, "set_position", {"uid": uid, "pos1": pos})
                await send(ws, "request_params", {"uid": uid})
            await drain(ws, 1.5)
            # pin stored gain to 1.0 so applied gain == the spatial factor
            for uid in uids:
                await send(ws, "set_param", {"uid": uid, "name": "gain", "value": 1.0})
            await drain(ws, 1.0)

            # --- 1. static exactness ---------------------------------------
            worst = 0.0
            for px, _ in ((2, 4), (5, 4), (8, 4)):
                gains = await set_point(ws, sim_log.name, px, 4)
                for device_id, (_, pos) in LAYOUT.items():
                    want = expected([px, 4], pos)
                    got = gains.get(device_id)
                    err = abs(got - want) if got is not None else 9.0
                    worst = max(worst, err)
                    check(f"point=({px},4) id={device_id} gain={want:.3f}",
                          got is not None and err <= TOL,
                          f"want={want:.4f} got={got}")
            check("static falloff exact across the sweep", worst <= TOL,
                  f"worst err={worst:.4f}")

            # --- 2. compose with master ------------------------------------
            await set_point(ws, sim_log.name, 5, 4)  # B at the point (factor 1.0)
            await send(ws, "set_master", {"value": 0.5})
            await drain(ws, 0.8)
            gains = read_gains(sim_log.name)
            check("master composes (stored x master x spatial)",
                  gains.get(2) is not None and abs(gains[2] - 0.5) <= TOL,
                  f"want=0.5 got={gains.get(2)}")
            await send(ws, "set_master", {"value": 1.0})
            await drain(ws, 0.8)

            # --- 3. dynamic envelope ---------------------------------------
            sim_log.seek(0, os.SEEK_END)
            sweep_start = sim_log.tell()
            await send(ws, "set_spatial", {"active": True, "radius": RADIUS,
                                           "falloff": "linear",
                                           "motion": {"type": "path", "duration": 6.0,
                                                      "points": [[0, 4], [10, 4]]}})
            await drain(ws, 6.5)
            with open(sim_log.name) as source:
                source.seek(sweep_start)
                window = source.read()
            series = []
            for order, line in enumerate(window.splitlines()):
                m = re.search(r"id=(\d+) .*p/gain=([-+\d.eE]+)", line)
                if m:
                    series.append((order, int(m.group(1)), float(m.group(2))))
            peak_at = {}
            peak_val = {}
            for order, device_id, gain in series:
                if gain >= peak_val.get(device_id, -1.0):
                    peak_val[device_id] = gain
                    peak_at[device_id] = order
            for device_id in LAYOUT:
                check(f"id={device_id} reaches full gain as the point passes",
                      peak_val.get(device_id, 0) >= 0.95,
                      f"peak={peak_val.get(device_id)}")
            check("peaks arrive in spatial order (a<b<c)",
                  device_id_order_ok(peak_at),
                  f"peak order={peak_at}")

            # --- 4. restore on deactivate ----------------------------------
            await send(ws, "set_spatial", {"active": False})
            await drain(ws, 0.8)
            gains = read_gains(sim_log.name)
            check("deactivate restores stored x master",
                  all(gains.get(i) is not None and abs(gains[i] - 1.0) <= TOL
                      for i in LAYOUT),
                  f"gains={gains}")

            # --- 5. regression ---------------------------------------------
            updates = []
            await send(ws, "set_param", {"uid": uids[0], "name": "gain2", "value": 0.4})
            await drain(ws, 1.0, updates)
            check("set_param still round-trips",
                  any(u.get("uid") == uids[0]
                      and abs(float(u.get("params", {}).get("gain2", -9)) - 0.4) < 1e-6
                      for u in updates),
                  f"updates={[u.get('uid') for u in updates]}")
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
    check("server logged no traceback", "Traceback" not in log_text, log_text[-500:])
    for path in (sim_log.name, server_log.name, state_file):
        try:
            os.unlink(path)
        except OSError:
            pass

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("spatial-0 engine checks passed")
    return 0


def device_id_order_ok(peak_at):
    return (1 in peak_at and 2 in peak_at and 3 in peak_at
            and peak_at[1] < peak_at[2] < peak_at[3])


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
