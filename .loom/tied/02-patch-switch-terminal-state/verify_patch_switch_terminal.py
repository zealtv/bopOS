#!/usr/bin/env python3
"""Focused bounded patch-switch lifecycle verification."""

import asyncio
import json
import os
import sys
import tempfile
from types import SimpleNamespace

from pythonosc.osc_message import OscMessage

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "dashboard", "server.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "dashboard"))
import server as server_module  # noqa: E402
from server import Dashboard  # noqa: E402
from state import patch_badge  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


class Sender:
    def __init__(self):
        self.frames = []

    def sendto(self, packet, destination):
        message = OscMessage(packet)
        self.frames.append((message.address, list(message.params), destination))

    def close(self):
        pass


def write_patch(root, name):
    path = os.path.join(root, name)
    os.makedirs(path)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(name.encode())
    with open(os.path.join(path, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": [],
                   "caps": [], "slots": []}, target)


def listing(alpha_fingerprint, active):
    return [
        {"name": "alpha", "active": active == "alpha", "git": False,
         "manifest": True, "fingerprint": alpha_fingerprint},
        {"name": "beta", "active": active == "beta", "git": False,
         "manifest": True, "fingerprint": "b" * 64},
    ]


async def exercise(root):
    assets = os.path.join(root, "assets")
    patches = os.path.join(root, "patches")
    os.makedirs(assets)
    write_patch(patches, "alpha")
    args = SimpleNamespace(
        state_file=os.path.join(root, "installation.json"), devices_file=None,
        listen_port=15593, send_port=16693, osc_target="127.0.0.1",
        assets_dir=assets, patches_dir=patches, port=18080, public_url=None,
        sim_audio_backend="none", sim_no_engine=True,
    )
    dashboard = Dashboard(args)
    dashboard.osc.sender = Sender()
    item = await dashboard.catalog_patch("alpha")
    desired = {"name": "alpha", "fingerprint": item["fingerprint"]}
    dashboard.state.stage_fleet_patch("alpha", item["fingerprint"])
    uid = "node-1"
    dashboard.state.seats["1"] = dashboard.state.clean_seat({
        "id": 1, "name": "one", "positions": [[1, 1]],
        "params": {}, "bound": uid})
    device = dashboard.state.ensure(uid)
    device.update(id=1, ip="10.0.0.2", online=True,
                  patches=listing(item["fingerprint"], "beta"),
                  report={"patch": "beta"})
    old_receipt = server_module.PATCH_SWITCH_RECEIPT_SECONDS
    old_reconcile = server_module.PATCH_SWITCH_RECONCILE_SECONDS
    server_module.PATCH_SWITCH_RECEIPT_SECONDS = .03
    server_module.PATCH_SWITCH_RECONCILE_SECONDS = .04
    try:
        await dashboard.switch_fleet_device(uid, "alpha", dashboard.fleet_generation)
        attempt = device["patch_switch"]
        check("normal switch starts in an explicit bounded state",
              attempt["status"] == "switching"
              and patch_badge(device, desired) == "switching")
        dashboard.osc.handle("/os/rev", ["abc", "persistent", uid], "10.0.0.2")
        check("receipt enters reconciliation instead of assuming success",
              device["patch_switch"] is attempt
              and attempt["status"] == "reconciling")
        dashboard.osc.handle("/os/patches", [json.dumps(
            listing(item["fingerprint"], "alpha"))], "10.0.0.2")
        check("normal observation proves success and clears the attempt",
              device["patch_switch"] is None
              and patch_badge(device, desired) == "current")

        device.update(patches=listing(item["fingerprint"], "beta"),
                      report={"patch": "beta"})
        await dashboard.switch_fleet_device(uid, "alpha", dashboard.fleet_generation)
        lost_receipt_attempt = device["patch_switch"]
        await asyncio.sleep(.04)
        check("lost receipt enters bounded fallback reconciliation",
              device["patch_switch"] is lost_receipt_attempt
              and lost_receipt_attempt["status"] == "reconciling")
        dashboard.osc.handle("/os/patches", [json.dumps(
            listing(item["fingerprint"], "alpha"))], "10.0.0.2")
        await asyncio.sleep(.05)
        check("later patch observation proves lost-receipt success",
              device["patch_switch"] is None
              and patch_badge(device, desired) == "current")

        device.update(patches=listing(item["fingerprint"], "beta"),
                      report={"patch": "beta"})
        await dashboard.switch_fleet_device(uid, "alpha", dashboard.fleet_generation)
        failed_attempt = device["patch_switch"]
        await asyncio.sleep(.09)
        check("contrary observation reaches a failed terminal state",
              device["patch_switch"] is failed_attempt
              and failed_attempt["status"] == "failed"
              and patch_badge(device, desired) == "failed",
              repr(failed_attempt))

        device.update(patches=None, report=None)
        await dashboard.switch_fleet_device(uid, "alpha", dashboard.fleet_generation)
        timeout_attempt = device["patch_switch"]
        await asyncio.sleep(.09)
        check("missing observation reaches a timeout terminal state",
              device["patch_switch"] is timeout_attempt
              and timeout_attempt["status"] == "timeout"
              and patch_badge(device, desired) == "timeout",
              repr(timeout_attempt))
        dashboard.osc.handle("/os/patches", [json.dumps(
            listing(item["fingerprint"], "beta"))], "10.0.0.2")
        check("late contrary observation upgrades timeout to failure",
              device["patch_switch"] is timeout_attempt
              and timeout_attempt["status"] == "failed"
              and patch_badge(device, desired) == "failed")
        dashboard.osc.handle("/os/patches", [json.dumps(
            listing(item["fingerprint"], "alpha"))], "10.0.0.2")
        check("late success observation clears a prior timeout",
              device["patch_switch"] is None
              and patch_badge(device, desired) == "current")

        device.update(patches=listing(item["fingerprint"], "beta"),
                      report={"patch": "beta"},
                      patch_switch={"patch": "alpha", "status": "failed",
                                    "reason": "fixture"})
        before = len(dashboard.osc.sender.frames)
        await dashboard.retry_fleet_patch(uid, None)
        retry_attempt = device["patch_switch"]
        check("one-device Retry starts a fresh switch attempt",
              retry_attempt["status"] == "switching"
              and len(dashboard.osc.sender.frames) == before + 1
              and dashboard.osc.sender.frames[-1][0] == "/1/os/patch"
              and dashboard.osc.sender.frames[-1][1] == ["alpha"])

        old_attempt = device["patch_switch"]
        dashboard.supersede_fleet_operation()
        check("new fleet generation invalidates the prior attempt token",
              device["patch_switch"] is None and old_attempt is not None)

        source = open(os.path.join(REPO, "dashboard", "static", "js", "dashboard.js"),
                      encoding="utf-8").read()
        check("terminal badges expose operator labels and Retry",
              'timeout:"switch timed out"' in source
              and 'failed:"switch failed"' in source
              and '"failed","timeout"' in source)
    finally:
        server_module.PATCH_SWITCH_RECEIPT_SECONDS = old_receipt
        server_module.PATCH_SWITCH_RECONCILE_SECONDS = old_reconcile
        await dashboard.stop()


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-switch-terminal-") as root:
        asyncio.run(exercise(root))
    total = 12
    print(f"\n{total - len(FAILURES)}/{total} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
