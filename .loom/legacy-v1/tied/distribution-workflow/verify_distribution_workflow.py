#!/usr/bin/env python3
"""Focused managed-simulation patch switch and real fetch URL verification."""

import asyncio
import json
import os
import socket
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest import mock

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "audition.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate repo")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "dashboard"))

from server import Dashboard  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_udp_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def write_patch(root, name):
    path = os.path.join(root, name)
    os.makedirs(path)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(name.encode())
    with open(os.path.join(path, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": [],
                   "caps": [], "slots": []}, target)


async def wait_virtual(dashboard, count, active_patch=None):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        virtual = [device for device in dashboard.state.devices.values()
                   if device.get("virtual")]
        if len(virtual) == count and all(device.get("patches") for device in virtual):
            if active_patch is None or all(any(
                    patch["name"] == active_patch and patch["active"]
                    for patch in device["patches"]) for device in virtual):
                return virtual
        await asyncio.sleep(.05)
    return [device for device in dashboard.state.devices.values() if device.get("virtual")]


async def main():
    with tempfile.TemporaryDirectory() as temp:
        patches = os.path.join(temp, "patches")
        assets = os.path.join(temp, "assets")
        os.makedirs(patches)
        write_patch(patches, "alpha")
        write_patch(patches, "beta")
        args = SimpleNamespace(
            state_file=os.path.join(temp, "installation.json"), devices_file=None,
            listen_port=free_udp_port(), send_port=free_udp_port(),
            osc_target="255.255.255.255", assets_dir=assets, patches_dir=patches,
            port=18080, public_url=None, sim_audio_backend="none", sim_no_engine=True,
            sim_engine_port_base=free_udp_port(),
        )
        dashboard = Dashboard(args)
        await dashboard.start()
        try:
            for seat_id in range(2):
                await dashboard.handle_ws({"type": "add_seat", "data": {
                    "id": seat_id, "name": f"seat-{seat_id}",
                    "positions": [[seat_id, 0]], "params": {}}})
            await dashboard.handle_ws({"type": "set_simulation", "data": {"active": True}})
            first = await wait_virtual(dashboard, 2, "alpha")
            old_process = dashboard.sim_process
            check("simulation exposes every valid host patch as installed",
                  len(first) == 2 and all(
                      {patch["name"] for patch in device.get("patches") or ()}
                      == {"alpha", "beta"} for device in first), repr(first))
            check("simulation starts one fleet-wide host patch",
                  dashboard.state.data["simulation"].get("patch") == "alpha")

            await dashboard.handle_ws({"type": "switch_patch", "data": {
                "uid": first[0]["uid"], "patch": "beta"}})
            second = await wait_virtual(dashboard, 2, "beta")
            check("simulated switch reaps and replaces the managed fleet",
                  old_process is not dashboard.sim_process and old_process.poll() is not None
                  and dashboard.sim_process.poll() is None)
            check("replacement fleet reports the selected patch active",
                  len(second) == 2 and dashboard.state.data["simulation"].get("patch") == "beta")
            await dashboard.handle_ws({"type": "send_distribution", "data": {
                "uid": second[0]["uid"], "kind": "patch", "name": "alpha"}})
            check("simulation backend never invents a pending file transfer",
                  not dashboard.osc.fetch_pending
                  and all(not device.get("fetch") for device in second))

            dashboard.state.ensure("real").update({"id": 0, "ip": "10.20.30.40"})
            ws = SimpleNamespace(url=SimpleNamespace(scheme="ws", hostname="127.0.0.1"),
                                 headers={"host": "127.0.0.1:18080"})
            route = mock.MagicMock()
            route.__enter__.return_value = route
            route.getsockname.return_value = ("10.20.30.5", 54321)
            with mock.patch("server.socket.socket", return_value=route):
                derived = dashboard.public_url(ws, "real")
            check("loopback browser URL derives a device-reachable LAN source",
                  derived == "http://10.20.30.5:18080", derived)

            dashboard.args.public_url = "http://dashboard.test:9999/"
            check("explicit public URL remains authoritative",
                  dashboard.public_url(ws, "real") == "http://dashboard.test:9999")
        finally:
            await dashboard.stop()

    source = open(os.path.join(REPO, "dashboard", "static", "js", "dashboard.js"),
                  encoding="utf-8").read()
    check("simulated UI removes byte distribution and explains host backing",
          "Host-backed simulated fleet" in source
          and "host patches need no Send step" in source
          and "simulating?'':`<section id=\"distribution\"" in source)
    check("real dropdown copy distinguishes installed from host patches",
          "The installed dropdown lists only patches acknowledged by this device" in source)

    print(f"\n{9 - len(FAILURES)}/9 passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
