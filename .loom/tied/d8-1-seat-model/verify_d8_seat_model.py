#!/usr/bin/env python3
"""Focused state/ws verification for dashboard seats."""
import asyncio
import json
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
from server import Dashboard
from state import InstallationState, SCHEMA
from osc_bridge import OSCBridge

FAIL = []
def check(label, ok):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    if not ok: FAIL.append(label)

class FakeOSC:
    def __init__(self): self.assigns = []
    def assign(self, uid, seat_id, name, positions):
        self.assigns.append((uid, seat_id, name, positions))
    def request(self, *args): pass
    def set_param(self, *args): pass
    def send_master(self, *args): pass
    def send_audition_listener(self): pass

async def main():
    with tempfile.TemporaryDirectory() as temp:
        path = os.path.join(temp, "installation.json")
        with open(path, "w", encoding="utf-8") as out:
            json.dump({"devices": {"old": {"id": 9}}}, out)
        state = InstallationState(path)
        check("old device schema is hard-broken", not state.seats and not state.devices)
        args = SimpleNamespace(state_file=path, devices_file=None, listen_port=15591,
            send_port=16691, osc_target="127.0.0.1", assets_dir=os.path.join(temp,"a"),
            patches_dir=os.path.join(temp,"p"), port=18191, public_url=None)
        dash = Dashboard(args); dash.osc = FakeOSC()
        await dash.handle_ws({"type":"add_seat","data":{"id":0,"name":"porch",
            "positions":[[1,2],[3,4]],"patch":"demo-pd","params":{"gain0":.8}}})
        check("seat authors before any device", dash.state.seats["0"]["bound"] is None
              and not dash.state.devices)
        one = dash.state.ensure("one"); one.update(online=True, id=-1)
        two = dash.state.ensure("two"); two.update(online=True, id=-1)
        await dash.handle_ws({"type":"bind_seat","data":{"id":0,"uid":"one"}})
        check("bind sends full ordinary assignment", dash.osc.assigns[-1] ==
              ("one",0,"porch",[[1.0,2.0],[3.0,4.0]]))
        await dash.handle_ws({"type":"unbind_seat","data":{"id":0}})
        await dash.handle_ws({"type":"bind_seat","data":{"id":0,"uid":"two"}})
        check("seat survives device swap", dash.state.seats["0"]["bound"] == "two"
              and dash.state.seats["0"]["params"]["gain0"] == .8)
        await dash.handle_ws({"type":"forget_device","data":{"uid":"two"}})
        check("forget unbinds first", "two" not in dash.state.devices
              and dash.state.seats["0"]["bound"] is None)
        stale = dash.state.ensure("stale"); stale["online"] = False
        live = dash.state.ensure("live"); live["online"] = True
        await dash.handle_ws({"type":"forget_offline_unbound","data":{}})
        check("bulk forget removes only offline unbound", "stale" not in dash.state.devices
              and "live" in dash.state.devices)
        dash.state.seats["0"]["bound"] = "live"
        dash.state.save_venue("room")
        dash.state.seats.clear()
        check("venue auto-rebinds currently live uid", dash.state.load_venue("room")
              and dash.state.seats["0"]["bound"] == "live")
        replay = []
        bridge = OSCBridge(dash.state, lambda *_: None, 15591, 16691, "127.0.0.1")
        bridge.sender = type("Sender", (), {"sendto": lambda *_: None})()
        bridge.assign = lambda uid, seat_id, name, positions: replay.append(
            (uid, seat_id, name, positions))
        dash.state.devices["live"]["online"] = False
        bridge.handle("/hb", ["live", 99, "rev", 1], "127.0.0.1")
        check("heartbeat replay reads authoritative bound seat", replay[-1] ==
              ("live", 0, "porch", [[1.0,2.0],[3.0,4.0]]))
        durable = dash.state.durable()
        check("durable schema carries seats, never roster", durable["schema"] == SCHEMA
              and "seats" in durable and "devices" not in durable)
    print(f"\n{9-len(FAIL)}/9 passed")
    return 1 if FAIL else 0
if __name__ == "__main__": raise SystemExit(asyncio.run(main()))
