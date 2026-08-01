#!/usr/bin/env python3
"""Focused browser-free verification of execution/physical OSC ownership."""

import asyncio
import os
import sys
from types import SimpleNamespace

from pythonosc.osc_message import OscMessage

sys.dont_write_bytecode = True

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "dashboard", "osc_bridge.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "dashboard"))

from osc_bridge import OSCBridge  # noqa: E402
from server import Dashboard  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


class State:
    def __init__(self):
        self.data = {
            "automation": {}, "muted": True, "master": 0.4,
            "points": {}, "groups": {}, "supervisor": {"mode": "simulate"},
        }
        self.devices = {
            "physical-1": {
                "uid": "physical-1", "id": 4, "online": True, "virtual": False,
            },
            "audition-0001": {
                "uid": "audition-0001", "id": 0, "online": True,
                "virtual": True, "seat_id": 0,
            },
        }
        self.seats = {
            "0": {
                "id": 0, "name": "Seat 0", "bound": "physical-1",
                "positions": [], "params": {}, "groups": [],
            },
        }
        self.device_registry = {
            "physical-1": {"device_enabled": True},
        }

    def public(self):
        return self.data

    def clean_seat_id(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def clean_group_id(self, value):
        return self.clean_seat_id(value)

    def seat_for_uid(self, uid):
        return next(
            (seat for seat in self.seats.values() if seat.get("bound") == uid),
            None)

    def save_debounced(self):
        pass

    def device_enabled_for(self, uid):
        return bool(self.device_registry.get(uid, {}).get("device_enabled", True))

    def set_device_enabled(self, uid, value):
        if uid not in self.device_registry or not isinstance(value, bool):
            return False
        self.device_registry[uid]["device_enabled"] = value
        return True


class Sender:
    def __init__(self):
        self.frames = []

    def sendto(self, packet, destination):
        message = OscMessage(packet)
        self.frames.append(
            (message.address, list(message.params), destination))

    def close(self):
        pass


class WS:
    def __init__(self):
        self.errors = []


def matching(sender, address):
    return [frame for frame in sender.frames if frame[0] == address]


async def verify():
    state = State()
    bridge = OSCBridge(
        state, lambda *_args: None, listen_port=5550, send_port=6660,
        target="192.0.2.255")
    sender = Sender()
    bridge.sender = sender
    bridge.set_target("127.0.0.1")

    bridge.set_device_enabled("physical-1", False)
    bridge.set_device_hostname("physical-1", "finn-jet")
    bridge.uid_action("physical-1", "identify")
    bridge.action("all", "reboot")
    bridge.assign("physical-1", 0, "Seat 0")
    bridge.send_groups("physical-1", [])
    bridge.os_command(4, "patch", ["alpha"])
    bridge.fetch("physical-1", "http://host/manifest", "slot", "sha")
    bridge.request("physical-1", "report")
    physical_frames = list(sender.frames)
    check(
        "physical administration ignores the Simulation execution target",
        physical_frames
        and all(frame[2] == ("192.0.2.255", 6660)
                for frame in physical_frames),
        repr(physical_frames))

    sender.frames.clear()
    bridge.assign("audition-0001", 0, "Seat 0")
    bridge.request("audition-0001", "report")
    virtual_frames = list(sender.frames)
    check(
        "virtual UID operations use the active execution target",
        virtual_frames
        and all(frame[2] == ("127.0.0.1", 6660)
                for frame in virtual_frames),
        repr(virtual_frames))

    sender.frames.clear()
    bridge.send_master()
    bridge.send_mute_all()
    bridge.set_param("all", "gain", 0.5)
    bridge.fire_cue_now("go")
    bridge.send_points_frame()
    execution_frames = list(sender.frames)
    check(
        "runtime controls use the active execution target",
        execution_frames
        and all(frame[2] == ("127.0.0.1", 6660)
                for frame in execution_frames),
        repr(execution_frames))

    sender.frames.clear()
    dashboard = Dashboard.__new__(Dashboard)
    dashboard.osc = bridge
    dashboard.performance_target = "192.0.2.255"
    dashboard.state = state
    dashboard.supervisor_lock = asyncio.Lock()
    dashboard.manifest_lock = asyncio.Lock()
    ws = WS()

    async def broadcast(*_args):
        pass

    async def ws_error(target, message):
        target.errors.append(message)

    dashboard.broadcast = broadcast
    dashboard.ws_error = ws_error
    state.data["supervisor"] = {"mode": "edit"}
    bridge.set_target("127.0.0.1")
    await dashboard.handle_ws({
        "type": "set_device_enabled",
        "data": {"uid": "physical-1", "value": 0},
    }, ws)
    await dashboard.handle_ws({
        "type": "mute_all", "data": {"value": 0},
    }, ws)
    edit_frames = list(sender.frames)
    check(
        "Patch Edit allows physical device controls on the LAN",
        edit_frames[0][:2] == (
            "/all/os/to", ["physical-1", "enabled", 0])
        and edit_frames[0][2] == ("192.0.2.255", 6660),
        repr(edit_frames))
    check(
        "Patch Edit allows MUTE ALL on the execution route",
        edit_frames[1][:2] == ("/all/os/mute", [0])
        and edit_frames[1][2] == ("127.0.0.1", 6660)
        and not ws.errors,
        repr((edit_frames, ws.errors)))

    sender.frames.clear()
    state.data["master"] = 0.4
    state.data["muted"] = True
    dashboard.restore_live_state()
    restored = list(sender.frames)
    check(
        "Live restore replays only master and MUTE ALL",
        [(address, args) for address, args, _destination in restored]
        == [
            ("/all/os/master", [0.4000000059604645]),
            ("/all/os/mute", [1]),
        ]
        and all(destination == ("192.0.2.255", 6660)
                for _address, _args, destination in restored),
        repr(restored))
    check(
        "Live restore emits no physical assignment or device mute",
        not matching(sender, "/all/os/assign")
        and not any(address == "/all/os/to" for address, _args, _dest in restored),
        repr(restored))

    for timeout in bridge.pending_timeouts.values():
        timeout.cancel()
    for records in bridge.fetch_pending.values():
        for record in records:
            record.get("timeout") and record["timeout"].cancel()
    bridge.pending_timeouts.clear()
    bridge.fetch_pending.clear()


def main():
    asyncio.run(verify())
    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
