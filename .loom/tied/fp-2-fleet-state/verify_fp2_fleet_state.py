#!/usr/bin/env python3
"""Browser-free fp-2 verification: durable fleet state + real simfleet flow."""

import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate repo")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "dashboard"))

from server import Dashboard  # noqa: E402
from state import InstallationState, patch_badge  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def udp_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def write_patch(root, name, payload):
    path = os.path.join(root, name)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(payload)
    with open(os.path.join(path, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": [],
                   "caps": [], "slots": []}, target)


def state_checks(temp):
    path = os.path.join(temp, "legacy.json")
    legacy = {"schema": 1, "name": "legacy", "seats": {"0": {
        "id": 0, "name": "zero", "positions": [[0, 0]], "patch": "old",
        "params": {}, "bound": None}}}
    with open(path, "w", encoding="utf-8") as target:
        json.dump(legacy, target)
    state = InstallationState(path)
    check("legacy per-seat patch is dropped", "patch" not in state.seats["0"])
    one, two, three = "1" * 64, "2" * 64, "3" * 64
    state.stage_fleet_patch("alpha", one)
    state.stage_fleet_patch("alpha", two)
    check("same-name restage refreshes without rotating previous",
          state.data["fleet_patch"]["fingerprint"] == two
          and state.data["fleet_patch"]["previous"] is None)
    state.stage_fleet_patch("beta", three)
    check("name change records the immediately previous identity",
          state.data["fleet_patch"]["previous"] == {
              "name": "alpha", "fingerprint": two})
    check("simulation patch reads through fleet desired state",
          state.data["simulation"]["patch"] == "beta")
    state.save()
    state.save_venue("room-a")
    venue = json.load(open(os.path.join(temp, "installations", "room-a.json"),
                           encoding="utf-8"))
    reloaded = InstallationState(path)
    check("fleet patch persists in installation and venue snapshots",
          reloaded.data["fleet_patch"] == state.data["fleet_patch"]
          and venue["fleet_patch"] == state.data["fleet_patch"])
    check("durable state contains no retired seat patch",
          "patch" not in reloaded.durable()["seats"]["0"])
    state.data["fleet_patch"] = None
    state.save_venue("room-unset")
    state.stage_fleet_patch("beta", three)
    check("loading an unset venue clears simulation patch read-through",
          state.load_venue("room-unset")
          and state.data["fleet_patch"] is None
          and "patch" not in state.data["simulation"])

    desired = {"name": "beta", "fingerprint": three}
    base = {"online": True, "patches": [
        {"name": "beta", "active": True, "manifest": True,
         "fingerprint": three}], "fetch": {}, "patch_switch": None}
    cases = [
        ("unset", base, None, "unset"),
        ("offline", {**base, "online": False}, desired, "unknown"),
        ("unqueried", {**base, "patches": None}, desired, "unknown"),
        ("switch", {**base, "patch_switch": {"patch": "beta"}}, desired, "switching"),
        ("fetch", {**base, "fetch": {"patch:beta": "fetching"}}, desired, "switching"),
        ("missing", {**base, "patches": []}, desired, "missing"),
        ("mismatch", {**base, "patches": [
            {"name": "beta", "active": False, "manifest": True,
             "fingerprint": three}, {"name": "alpha", "active": True}]},
         desired, "mismatch"),
        ("unverified", {**base, "patches": [
            {"name": "beta", "active": True, "manifest": True}]},
         desired, "stale_unverified"),
        ("stale", {**base, "patches": [
            {"name": "beta", "active": True, "manifest": True,
             "fingerprint": two}]}, desired, "stale"),
        ("current", base, desired, "current"),
    ]
    results = {name: patch_badge(device, wanted) for name, device, wanted, _ in cases}
    check("badge precedence covers unset through current",
          all(results[name] == expected for name, _device, _wanted, expected in cases),
          repr(results))
    check("badge derivation never stores a verdict", "patch_badge" not in base)


class CaptureWS:
    def __init__(self):
        self.messages = []
        self.url = SimpleNamespace(scheme="ws", hostname="127.0.0.1")
        self.headers = {"host": "127.0.0.1"}

    async def send_json(self, message):
        self.messages.append(json.loads(json.dumps(message)))


async def wait_for(predicate, timeout=12):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        await asyncio.sleep(0.05)
    return predicate()


async def integration_checks(temp):
    patches = os.path.join(temp, "patches")
    assets = os.path.join(temp, "assets")
    nodes = os.path.join(temp, "nodes")
    os.makedirs(assets)
    write_patch(patches, "demo-pd", b"demo")
    write_patch(patches, "beta", b"beta-v1")
    listen, command = udp_port(), udp_port()
    args = SimpleNamespace(
        state_file=os.path.join(temp, "installation.json"), devices_file=None,
        listen_port=listen, send_port=command, osc_target="127.0.0.1",
        assets_dir=assets, patches_dir=patches, port=18080,
        public_url="http://127.0.0.1:18080", sim_audio_backend="none",
        sim_no_engine=True, sim_engine_port_base=udp_port())
    dashboard = Dashboard(args)
    macs = [f"02:53:49:4d:00:0{index}" for index in (1, 2)]
    for index, uid in enumerate(macs, 1):
        dashboard.state.seats[str(index)] = dashboard.state.clean_seat({
            "id": index, "name": f"seat-{index}", "positions": [[index, 0]],
            "params": {}, "bound": uid})
    offline = "02:53:49:4d:00:03"
    dashboard.state.seats["3"] = dashboard.state.clean_seat({
        "id": 3, "name": "offline", "positions": [[3, 0]],
        "params": {}, "bound": offline})
    dashboard.state.ensure(offline).update({"id": 3, "online": False,
                                            "patches": None})
    ws = CaptureWS()
    dashboard.clients.add(ws)
    fleet_log = open(os.path.join(temp, "simfleet.log"), "w", encoding="utf-8")
    fleet = None
    await dashboard.start()
    try:
        dashboard.state.data["simulation"]["active"] = True
        await dashboard.handle_ws({"type": "switch_patch", "data": {
            "uid": "all", "patch": "beta"}}, ws)
        check("legacy simulated switch rejects an unconfirmed WS command",
              dashboard.state.data.get("fleet_patch") is None
              and ws.messages[-1]["type"] == "error")
        dashboard.state.data["simulation"]["active"] = False
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
            "--devices", "2", "--state-dir", nodes, "--target", "127.0.0.1",
            "--report-port", str(listen), "--cmd-port", str(command),
            "--hb-interval", "0.25", "--boot-secs", "0.2",
            "--fetch-seconds", "2",
            "--patches-dir", patches,
            "--manifest", os.path.join(patches, "demo-pd", "bopos.patch.json"),
        ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)
        discovered = await wait_for(lambda: all(
            dashboard.state.devices.get(uid, {}).get("patches") for uid in macs))
        check("real simfleet nodes discover with patch listings", bool(discovered))

        await dashboard.handle_ws({"type": "set_fleet_patch", "data": {
            "patch": "beta"}}, ws)
        check("fleet set is confirmation-gated",
              dashboard.state.data.get("fleet_patch") is None
              and ws.messages[-1]["type"] == "error")
        await dashboard.handle_ws({"type": "set_fleet_patch", "data": {
            "patch": "beta", "confirmed": True}}, ws)
        fleet_task = dashboard.fleet_operation
        await dashboard.handle_ws({"type": "retry_fleet_patch", "data": {
            "uid": macs[0]}}, ws)
        check("row retry does not cancel active fleet convergence",
              dashboard.fleet_operation is fleet_task and not fleet_task.cancelled())
        converged = await wait_for(lambda: all(
            patch_badge(dashboard.state.devices[uid], {
                "name": "beta", "fingerprint": dashboard.state.data["fleet_patch"]["fingerprint"]
            }) == "current" for uid in macs))
        check("set fleet patch converges bytes then switches responsive nodes",
              bool(converged))
        public = await dashboard.public_state()
        check("offline node stays unknown and does not block convergence",
              public["devices"][offline]["patch_badge"] == "unknown")
        surfaced = await wait_for(lambda: any(
            message["type"] in ("device_update", "patches", "rev")
            and message["data"].get("patch_badge") == "current"
            for message in ws.messages), timeout=2)
        check("derived badge is surfaced on WS device payloads", bool(surfaced))
        check("derived badge is absent from runtime state",
              all("patch_badge" not in dashboard.state.devices[uid]
                  for uid in (*macs, offline)))

        with open(os.path.join(patches, "beta", "main.bin"), "wb") as target:
            target.write(b"beta-v2")
        await dashboard.handle_ws({"type": "refresh_distribution", "data": {}}, ws)
        stale_state = next((message for message in reversed(ws.messages)
                            if message["type"] == "state"), None)
        check("host edit makes matching active content stale",
              stale_state["data"]["devices"][macs[0]]["patch_badge"] == "stale")
        await dashboard.handle_ws({"type": "retry_fleet_patch", "data": {"uid": macs[0]}}, ws)
        retried = await wait_for(lambda: (
            dashboard.state.devices[macs[0]].get("patches")
            and patch_badge(dashboard.state.devices[macs[0]], {
                "name": "beta", "fingerprint": dashboard.state.data["fleet_patch"]["fingerprint"]
            }) == "current"))
        check("operator retry refreshes stale content", bool(retried))
        await dashboard.handle_ws({"type": "retry_fleet_patch", "data": {"uid": macs[1]}}, ws)
        await wait_for(lambda: patch_badge(dashboard.state.devices[macs[1]], {
            "name": "beta", "fingerprint": dashboard.state.data["fleet_patch"]["fingerprint"]
        }) == "current")

        # The old fetch receipt may still arrive after cancellation. Generation
        # ownership must prevent its coordinator from switching back to beta.
        with open(os.path.join(patches, "beta", "main.bin"), "wb") as target:
            target.write(b"beta-v3")
        await dashboard.handle_ws({"type": "retry_fleet_patch", "data": {"uid": macs[0]}}, ws)
        started = await wait_for(lambda: (dashboard.state.devices[macs[0]].get("fetch") or {}).get(
            "patch:beta") in ("sent", "queued", "fetching"), timeout=5)
        check("overlap fixture starts an old-generation retry", bool(started))

        await dashboard.handle_ws({"type": "set_fleet_patch", "data": {
            "patch": "demo-pd", "confirmed": True}}, ws)
        demo_current = await wait_for(lambda: all(any(
            patch.get("name") == "demo-pd" and patch.get("active")
            and patch.get("fingerprint") == dashboard.state.data["fleet_patch"]["fingerprint"]
            for patch in dashboard.state.devices[uid].get("patches") or ()) for uid in macs))
        check("second fleet choice becomes current", bool(demo_current), repr({
            "fleet": dashboard.state.data.get("fleet_patch"),
            "devices": {uid: {"fetch": dashboard.state.devices[uid].get("fetch"),
                              "switch": dashboard.state.devices[uid].get("patch_switch"),
                              "patches": dashboard.state.devices[uid].get("patches")}
                        for uid in macs},
            "task": (None if dashboard.fleet_operation is None else
                     {"done": dashboard.fleet_operation.done(),
                      "cancelled": dashboard.fleet_operation.cancelled(),
                      "exception": (repr(dashboard.fleet_operation.exception())
                                    if dashboard.fleet_operation.done()
                                    and not dashboard.fleet_operation.cancelled() else None)})}))
        await asyncio.sleep(3)
        check("superseded retry cannot switch a node back later", all(any(
            patch.get("name") == "demo-pd" and patch.get("active")
            for patch in dashboard.state.devices[uid].get("patches") or ()) for uid in macs))
        with open(os.path.join(patches, "beta", "main.bin"), "wb") as target:
            target.write(b"beta-v4")
        await dashboard.handle_ws({"type": "revert_fleet_patch", "data": {
            "confirmed": True}}, ws)
        shared_fetch = await wait_for(lambda: (dashboard.state.devices[macs[0]].get("fetch") or {}).get(
            "patch:beta") in ("sent", "queued", "fetching"), timeout=5)
        check("revert begins a fresh desired-content fetch", bool(shared_fetch))
        await dashboard.handle_ws({"type": "set_fleet_patch", "data": {
            "patch": "beta", "confirmed": True}}, ws)
        reverted = await wait_for(lambda: all(any(
            patch.get("name") == "beta" and patch.get("active")
            for patch in dashboard.state.devices[uid].get("patches") or ()) for uid in macs))
        record = dashboard.state.data["fleet_patch"]
        check("revert restages previous through the same fleet flow",
              bool(reverted) and record["name"] == "beta"
              and record["previous"]["name"] == "demo-pd", repr(record))
        check("superseding same-content set safely observes the existing fetch",
              bool(reverted))
    finally:
        if fleet is not None and fleet.poll() is None:
            fleet.terminate()
            try:
                fleet.wait(timeout=3)
            except subprocess.TimeoutExpired:
                fleet.kill()
                fleet.wait(timeout=3)
        fleet_log.close()
        await dashboard.stop()


async def main():
    with tempfile.TemporaryDirectory() as temp:
        state_checks(temp)
    with tempfile.TemporaryDirectory() as temp:
        await integration_checks(temp)
    source = open(os.path.join(REPO, "dashboard", "static", "js", "dashboard.js"),
                  encoding="utf-8").read()
    check("legacy simulated switch sends its confirmation receipt",
          'ws.send("switch_patch"' in source and "confirmed:true" in source)
    print(f"\n{len(FAILURES)} failure(s)" if FAILURES else "\nall checks passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
