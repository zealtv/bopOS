#!/usr/bin/env python3
"""Focused command routing and reconnect assignment checks."""
import asyncio
import os
import sys
import tempfile
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, "dashboard"))
from osc_bridge import OSCBridge  # noqa: E402
from server import Dashboard  # noqa: E402
from state import InstallationState  # noqa: E402

FAILURES = []


def check(label, condition):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}")
    if not condition:
        FAILURES.append(label)


class FakeOSC:
    def __init__(self):
        self.commands = []

    def action(self, selector, verb):
        self.commands.append(("action", selector, verb, []))

    def os_command(self, selector, verb, args=()):
        self.commands.append(("os", selector, verb, list(args)))


async def main():
    with tempfile.TemporaryDirectory() as temp:
        args = SimpleNamespace(
            state_file=os.path.join(temp, "installation.json"), devices_file=None,
            listen_port=15595, send_port=16695, osc_target="127.0.0.1",
            assets_dir=os.path.join(temp, "assets"),
            patches_dir=os.path.join(temp, "patches"), port=18195, public_url=None,
        )
        dashboard = Dashboard(args)
        dashboard.osc = FakeOSC()
        seat = dashboard.state.clean_seat({"id": 0, "name": "Seat 0",
            "positions": [[1, 2]], "patch": "demo-pd", "params": {},
            "bound": "box"})
        dashboard.state.seats["0"] = seat
        dashboard.state.ensure("box")["online"] = True
        await dashboard.handle_ws({"type": "action", "data": {
            "uid": "box", "verb": "shutdown"}})
        check("bound seat zero routes lifecycle action with selector zero",
              dashboard.osc.commands[-1] == ("action", 0, "shutdown", []))
        await dashboard.handle_ws({"type": "identify", "data": {"uid": "box"}})
        check("identify stays UID-targeted on the all selector",
              dashboard.osc.commands[-1] == ("os", "all", "identify", ["box"]))

        state = InstallationState(os.path.join(temp, "bridge.json"))
        state.seats["0"] = state.clean_seat({"id": 0, "name": "Seat 0",
            "positions": [[1, 2]], "patch": "demo-pd", "params": {},
            "bound": "box"})
        bridge = OSCBridge(state, lambda *_: None, 15596, 16696, "127.0.0.1")
        bridge.sender = type("Sender", (), {"sendto": lambda *_: None})()
        replay = []
        bridge.assign = lambda *values: replay.append(("assign", *values))
        bridge.os_command = lambda selector, verb, values=(): replay.append(
            ("os", selector, verb, list(values)))
        bridge.request = lambda *_: None
        bridge.handle("/hb", ["box", 99, "rev", 1], "127.0.0.1")
        check("online appearance replays authoritative seat assignment",
              replay[0] == ("assign", "box", 0, "Seat 0", [[1.0, 2.0]]))
        check("appearance replay never infers or changes mute state",
              all(command[0] != "os" or command[2] != "mute"
                  for command in replay))

    print(f"\n{4-len(FAILURES)}/4 passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
