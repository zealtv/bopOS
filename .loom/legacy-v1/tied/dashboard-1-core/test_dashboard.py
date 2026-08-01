#!/usr/bin/env python3
"""End-to-end checks for the phase-one bopOS dashboard."""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time

import websockets


# locate the repo by marker, not by depth — the loom moves this file
# from threads/<t>/<stitch>.stitching/ to tied/<stitch>/ when tied
REPO = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent
FAILURES = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print("[{}] {}{}".format(status, label, " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


async def wait_message(ws, wanted, timeout=5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        message = json.loads(await asyncio.wait_for(ws.recv(), end - time.monotonic()))
        if message.get("type") == wanted:
            return message
    raise asyncio.TimeoutError(wanted)


async def wait_devices(ws):
    devices = {}
    end = time.monotonic() + 5
    while len(devices) < 3 and time.monotonic() < end:
        message = json.loads(await asyncio.wait_for(ws.recv(), end - time.monotonic()))
        if message.get("type") == "device_update":
            device = message["data"]
            devices[device["uid"]] = device
    return devices


async def wait_log(process, needle, timeout=5):
    end = time.monotonic() + timeout
    lines = []
    while time.monotonic() < end:
        line = await asyncio.wait_for(asyncio.to_thread(process.stdout.readline), end - time.monotonic())
        if not line:
            break
        lines.append(line.rstrip())
        if needle in line:
            return True, "\n".join(lines)
    return False, "\n".join(lines)


async def run():
    with tempfile.TemporaryDirectory() as temp:
        state_file = os.path.join(temp, "installation.json")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"), "--port", "18080",
            "--listen-port", "15550", "--send-port", "16660", "--osc-target", "127.0.0.1",
            "--state-file", state_file,
        ], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "3",
            "--unassigned", "1", "--target", "127.0.0.1", "--report-port", "15550",
            "--cmd-port", "16660", "--hb-interval", "1.0",
        ], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            ws = None
            for _ in range(50):
                try:
                    ws = await websockets.connect("ws://127.0.0.1:18080/ws")
                    break
                except OSError:
                    await asyncio.sleep(.1)
            check("server accepts websocket", ws is not None)
            if ws is None:
                return
            async with ws:
                initial = json.loads(await asyncio.wait_for(ws.recv(), 3))
                check("initial state message", initial.get("type") == "state", repr(initial))
                devices = await wait_devices(ws)
                expected = {"02:53:49:4d:00:01", "02:53:49:4d:00:02", "02:53:49:4d:00:03"}
                check("three simulated devices discovered", set(devices) == expected, repr(devices.keys()))
                check("two assigned and one unassigned",
                      sorted(device["id"] for device in devices.values()) == [-1, 1, 2])
                uid = "02:53:49:4d:00:01"
                await ws.send(json.dumps({"type": "request_params", "data": {"uid": uid}}))
                params = (await wait_message(ws, "params_declaration"))["data"]
                check("manifest declares three params", len(params.get("declared", [])) == 3,
                      repr(params.get("declared")))
                await ws.send(json.dumps({"type": "request_report", "data": {"uid": uid}}))
                report = (await wait_message(ws, "report"))["data"].get("report", {})
                check("report contract version", report.get("contract_version") == "1.0", repr(report))
                await ws.send(json.dumps({"type": "set_param", "data":
                                         {"uid": uid, "name": "gain", "value": .5}}))
                logged, detail = await wait_log(fleet, "command=gain 0.5")
                check("simfleet receives parameter", logged, detail)
                await asyncio.sleep(1.2)
                persisted = json.load(open(state_file, encoding="utf-8"))
                check("parameter persists", persisted["devices"][uid]["params"]["gain"] == .5,
                      repr(persisted))
                await ws.send(json.dumps({"type": "action", "data": {"uid": uid, "verb": "aloha"}}))
                logged, detail = await wait_log(fleet, "command=aloha 1")
                check("simfleet receives aloha", logged, detail)
                await ws.send(json.dumps({"type": "mute_all", "data": {"value": 1}}))
                logged, detail = await wait_log(fleet, "muted=1")
                check("simfleet receives master mute", logged, detail)
        finally:
            for process in (fleet, server):
                process.terminate()
            for process in (fleet, server):
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()


asyncio.run(run())

# The undeclared path can't be reached through simfleet (it always serves the
# default manifest), so drive the bridge directly: an empty /os/params reply
# is the legal no-manifest answer and must yield the legacy four + the badge.
import types

sys.path.insert(0, os.path.join(REPO, "dashboard"))
import osc_bridge

events = []
state = types.SimpleNamespace(
    devices={"u1": {"uid": "u1", "id": 1, "ip": "10.0.0.7", "params": {}}},
    save_debounced=lambda: None)
bridge = osc_bridge.OSCBridge(state, lambda kind, data: events.append(kind), 0, 0, "127.0.0.1")
bridge.pending["params"].append("u1")
bridge.handle("/os/params", [], "10.0.0.7")
device = state.devices["u1"]
check("empty params reply yields legacy four with undeclared badge",
      device.get("undeclared") is True
      and [p["name"] for p in device.get("declared", [])] == ["gain", "gain2", "backing", "echo"]
      and device["params"].get("gain") == 0.75
      and events == ["params_declaration"],
      repr(device))

print()
if FAILURES:
    print("{} FAILURE(S): {}".format(len(FAILURES), FAILURES))
    sys.exit(1)
print("all checks passed")
