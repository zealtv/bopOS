#!/usr/bin/env python3
"""Focused verification for delayed managed-audition parameter catch-up."""

import asyncio
import json
import os
import sys
import tempfile

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
sys.path.insert(0, REPO)

import osc_bridge as bridge_module  # noqa: E402
from osc_bridge import OSCBridge  # noqa: E402
from state import InstallationState  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


class FakeSender:
    def __init__(self):
        self.frames = []

    def sendto(self, packet, destination):
        message = OscMessage(packet)
        self.frames.append((message.address, list(message.params), destination))

    def close(self):
        pass


def count(frames, address):
    return sum(frame_address == address for frame_address, _args, _dest in frames)


async def exercise(root):
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump({
            "schema": 1, "name": "catchup", "master": 0.5,
            "seats": {"0": {"id": 0, "name": "Seat 0",
                              "positions": [[0, 0]],
                              "params": {"gain": 0.75}, "bound": None}},
        }, target)
    state = InstallationState(state_path)
    state.data["supervisor"] = {"mode": "simulate"}
    broadcasts = []
    bridge = OSCBridge(state, lambda kind, data: broadcasts.append((kind, data)),
                       15550, 16660, "127.0.0.1")
    sender = FakeSender()
    bridge.sender = sender
    original_delays = bridge_module.AUDITION_PARAM_REPLAY_SECONDS
    bridge_module.AUDITION_PARAM_REPLAY_SECONDS = (0.05, 0.12)
    declaration = json.dumps({"params": [{
        "name": "gain", "type": "f", "min": 0, "max": 1,
        "default": 0.75, "group": "mix", "facilitator": True,
    }]})
    try:
        bridge.handle("/hb", ["audition-0001", 0, "verify", 1], "127.0.0.1")
        check("first virtual heartbeat requests params immediately",
              count(sender.frames, "/0/os/params") == 1,
              repr(sender.frames))

        bridge.handle("/os/params", [declaration], "127.0.0.1")
        immediate = list(sender.frames)
        check("immediate declaration pushes dashboard gain and master",
              any(address == "/0/p/gain" and abs(args[0] - 0.75) < 1e-5
                  for address, args, _dest in immediate)
              and any(address == "/0/os/master" and abs(args[0] - 0.5) < 1e-5
                      for address, args, _dest in immediate))

        await asyncio.sleep(0.07)
        check("first bounded post-load replay requests params again",
              count(sender.frames, "/0/os/params") == 2,
              repr(sender.frames))
        before_reply = len(sender.frames)
        bridge.handle("/os/params", [declaration], "127.0.0.1")
        replayed = sender.frames[before_reply:]
        check("post-load reply replays gain and master",
              any(address == "/0/p/gain" and abs(args[0] - 0.75) < 1e-5
                  for address, args, _dest in replayed)
              and any(address == "/0/os/master" and abs(args[0] - 0.5) < 1e-5
                      for address, args, _dest in replayed))

        await asyncio.sleep(0.07)
        check("second bounded replay covers slower-loading patches",
              count(sender.frames, "/0/os/params") == 3,
              repr(sender.frames))
    finally:
        bridge_module.AUDITION_PARAM_REPLAY_SECONDS = original_delays
        bridge.close()
        await state.close()


async def exercise_stopped_scope(root):
    state_path = os.path.join(root, "stopped.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump({"schema": 1, "name": "stopped", "seats": {
            "0": {"id": 0, "name": "Seat 0", "positions": [[0, 0]],
                  "params": {"gain": 0.75}, "bound": None}}}, target)
    state = InstallationState(state_path)
    state.data["supervisor"] = {"mode": "simulate"}
    bridge = OSCBridge(state, lambda _kind, _data: None,
                       15551, 16661, "127.0.0.1")
    sender = FakeSender()
    bridge.sender = sender
    original_delays = bridge_module.AUDITION_PARAM_REPLAY_SECONDS
    bridge_module.AUDITION_PARAM_REPLAY_SECONDS = (0.04,)
    try:
        bridge.handle("/hb", ["audition-0001", 0, "verify", 1], "127.0.0.1")
        initial = count(sender.frames, "/0/os/params")
        state.data["supervisor"] = {"mode": "off"}
        await asyncio.sleep(0.06)
        check("replay is suppressed after supervisor stops",
              count(sender.frames, "/0/os/params") == initial)
    finally:
        bridge_module.AUDITION_PARAM_REPLAY_SECONDS = original_delays
        bridge.close()
        await state.close()


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-param-catchup-") as root:
        asyncio.run(exercise(root))
        asyncio.run(exercise_stopped_scope(root))
    total = 6
    print(f"\n{total - len(FAILURES)}/{total} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
