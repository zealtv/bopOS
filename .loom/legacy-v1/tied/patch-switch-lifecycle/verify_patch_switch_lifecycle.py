#!/usr/bin/env python3
"""Focused engine-only patch switch verification."""

import asyncio
import heapq
import json
import os
import sys
import tempfile
import types

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    REPO = os.path.dirname(REPO)
sys.path[:0] = [os.path.join(REPO, "python"), os.path.join(REPO, "python", "io"),
                os.path.join(REPO, "tools"), os.path.join(REPO, "dashboard")]

import pyOSC3  # noqa: E402


class FakeServer:
    def __init__(self, _target):
        self.handlers = {}

    def addMsgHandler(self, address, callback):
        self.handlers[address] = callback

    def close(self):
        pass


class FakeClient:
    def connect(self, _target):
        pass

    def send(self, _message):
        pass


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
sys.argv = ["bopos.py", "unknown"]

import bopos  # noqa: E402
import manifest  # noqa: E402
import simfleet  # noqa: E402
from osc_bridge import OSCBridge  # noqa: E402
from state import InstallationState  # noqa: E402
from pythonosc import osc_message, osc_message_builder  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def write_patch(root, name):
    path = os.path.join(root, "patches", name)
    os.makedirs(path)
    with open(os.path.join(path, "main.bin"), "w", encoding="utf-8") as target:
        target.write(name)
    with open(os.path.join(path, manifest.MANIFEST_NAME), "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": [],
                   "caps": [], "slots": []}, target)


def real_node_check():
    old_dir, old_run = bopos.BOPOS_DIR, bopos.run_command
    old_alive, old_wake = bopos.engine_alive, bopos.hb_wake
    try:
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "run"))
            write_patch(root, "old")
            write_patch(root, "new")
            active = os.path.join(root, "patches", "active_patch.txt")
            with open(active, "w", encoding="utf-8") as target:
                target.write("old\n")
            commands = []
            bopos.BOPOS_DIR = root
            bopos.run_command = lambda argv, wait_for_start=False: (
                commands.append((tuple(argv), wait_for_start)) or 0)
            bopos.engine_alive = lambda: 1
            bopos.hb_wake = types.SimpleNamespace(set=lambda: commands.append(("heartbeat", False)))
            result = bopos.switch_patch_callback(args=["new"])
            selected = open(active, encoding="utf-8").read().strip()
            check("real switch selects the validated patch", result is True and selected == "new")
            scripts = [os.path.basename(command[0][1]) for command in commands
                       if isinstance(command[0], tuple)]
            check("real switch stops then starts only the engine stack",
                  scripts == ["stop-engine.sh", "start-engine.sh"], repr(commands))
            check("replacement launch is awaited before convergence",
                  any(isinstance(command[0], tuple) and command[1] is True
                      for command in commands), repr(commands))

            with open(active, "w", encoding="utf-8") as target:
                target.write("old\n")
            attempts = {"starts": 0}
            def fail_new_start(argv, wait_for_start=False):
                if os.path.basename(argv[1]) == "start-engine.sh":
                    attempts["starts"] += 1
                    return 1 if attempts["starts"] == 1 else 0
                return 0
            bopos.run_command = fail_new_start
            result = bopos.switch_patch_callback(args=["new"])
            check("failed replacement restores and relaunches the prior patch",
                  result is False and open(active, encoding="utf-8").read().strip() == "old"
                  and attempts["starts"] == 2)
    finally:
        bopos.BOPOS_DIR, bopos.run_command = old_dir, old_run
        bopos.engine_alive, bopos.hb_wake = old_alive, old_wake


class SimSocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        message = osc_message.OscMessage(data)
        self.calls.append((message.address, list(message.params), target))

    def setsockopt(self, *_args):
        pass

    def bind(self, _target):
        pass

    def setblocking(self, _value):
        pass


def simfleet_check():
    args = types.SimpleNamespace(protocol="v1", cmd_port=0, target="127.0.0.1",
        report_port=5550, drop=0.0, jitter_ms=0.0, state_dir=None,
        hb_interval=10.0, boot_secs=1.0, sync_skew_ms=0.0, sync_jitter_ms=0.0)
    device = simfleet.Device("02:00:00:00:00:01", "sim", 1, "abc1234")
    device.state = "running"
    device.patches["new"] = {"git": False, "manifest": True}
    old_socket = simfleet.socket.socket
    simfleet.socket.socket = lambda *_args: SimSocket()
    try:
        fleet = simfleet.SimFleet(args, [device])
    finally:
        simfleet.socket.socket = old_socket
    builder = osc_message_builder.OscMessageBuilder(address="/1/os/patch")
    builder.add_arg("new")
    fleet.receive_contract(builder.build().dgram, ("127.0.0.1", 4000))
    check("sim switch keeps helper/device running while engine stops",
          device.state == "running" and device.engine_alive() == 0)
    while fleet.events:
        _when, _sequence, callback, values = heapq.heappop(fleet.events)
        callback(*values)
    check("sim receipt follows replacement engine restart",
          device.engine_alive() == 1 and device.active_patch == "new"
          and fleet.sock.calls[-1][0] == "/os/rev", repr(fleet.sock.calls))


class Sender:
    def __init__(self):
        self.packets = []

    def sendto(self, packet, destination):
        self.packets.append((osc_message.OscMessage(packet).address, destination))

    def close(self):
        pass


async def dashboard_check():
    with tempfile.TemporaryDirectory() as temp:
        state = InstallationState(os.path.join(temp, "installation.json"))
        device = state.ensure("node")
        device.update(id=1, ip="10.0.0.2", online=True,
                      patch_switch={"patch": "new", "at": 1})
        broadcasts = []
        bridge = OSCBridge(state, lambda kind, data: broadcasts.append((kind, data)),
                           15590, 16690, "127.0.0.1")
        bridge.sender = Sender()
        bridge.handle("/os/rev", ["abc1234", "persistent", "node"], "10.0.0.2")
        addresses = [address for address, _target in bridge.sender.packets]
        check("convergence clears visible switching state", device["patch_switch"] is None)
        check("convergence refreshes patches, params, and report",
              addresses == ["/1/os/patches", "/1/os/params", "/1/os/report"],
              repr(addresses))
        bridge.close()


def source_checks():
    ui = open(os.path.join(REPO, "dashboard", "static", "js", "dashboard.js"),
              encoding="utf-8").read()
    contract = open(os.path.join(REPO, "docs", "OSC-CONTRACT.md"),
                    encoding="utf-8").read()
    check("UI says engine restart, not device reboot",
          "Only the audio engine restarts; the device stays online." in ui)
    check("contract records engine-only patch selection",
          "It never reboots the device." in contract)


def main():
    real_node_check()
    simfleet_check()
    asyncio.run(dashboard_check())
    source_checks()
    print(f"\n{10 - len(FAILURES)}/10 passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
