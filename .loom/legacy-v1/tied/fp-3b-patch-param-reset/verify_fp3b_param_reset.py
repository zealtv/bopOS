#!/usr/bin/env python3
"""Verify fleet patch-name transitions replace the one parameter schema."""

import asyncio
import json
import os
import socket
import sys
import tempfile
import time
from types import SimpleNamespace

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


def udp_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def write_patch(root, name, params):
    path = os.path.join(root, name)
    os.makedirs(path)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(name.encode())
    with open(os.path.join(path, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": params,
                   "caps": [], "slots": []}, target)


async def wait_for(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        await asyncio.sleep(.05)
    return predicate()


class CaptureWS:
    def __init__(self):
        self.messages = []
        self.url = SimpleNamespace(scheme="ws", hostname="127.0.0.1")
        self.headers = {"host": "127.0.0.1"}

    async def send_json(self, message):
        self.messages.append(json.loads(json.dumps(message)))


async def integration(temp):
    patches = os.path.join(temp, "patches")
    assets = os.path.join(temp, "assets")
    os.makedirs(assets)
    write_patch(patches, "demo", [
        {"name": "gain0", "type": "f", "min": 0, "max": 1, "default": .3},
        {"name": "trigger", "type": "i", "min": 0, "max": 1},
    ])
    write_patch(patches, "bonks", [
        {"name": "gain", "type": "f", "min": 0, "max": 1, "default": .75},
    ])
    state_path = os.path.join(temp, "installation.json")
    state = {"schema": 1, "name": "param-reset", "seats": {
        str(index): {"id": index, "name": f"seat-{index}",
                     "positions": [[index, 0]], "params": {
                         "gain": 0, "gain0": .1, "obsolete": index},
                     "bound": None}
        for index in range(2)}}
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    args = SimpleNamespace(
        state_file=state_path, devices_file=None,
        listen_port=udp_port(), send_port=udp_port(), osc_target="127.0.0.1",
        assets_dir=assets, patches_dir=patches, port=18080, public_url=None,
        sim_audio_backend="none", sim_no_engine=True,
        sim_engine_port_base=26661)
    dashboard = Dashboard(args)
    ws = CaptureWS()
    dashboard.clients.add(ws)
    await dashboard.start()
    try:
        # Migration fixture: fp-3 installations already have a desired patch,
        # but predate the schema marker and may contain values from older
        # manifests. The first same-name stage must repair them exactly once.
        dashboard.state.stage_fleet_patch("demo", "0" * 64)
        dashboard.stage_catalog_patch(await dashboard.catalog_patch("demo"))
        check("missing schema marker repairs an existing same-name installation",
              dashboard.state.data["params_patch"] == "demo"
              and all(seat["params"] == {"gain0": .3}
                      for seat in dashboard.state.seats.values()))
        await dashboard.start_simulation()
        demo_ready = await wait_for(lambda: len([
            device for device in dashboard.state.devices.values()
            if device.get("virtual") and device.get("declared")]) == 2)
        check("initial managed simulation adopts the selected manifest schema",
              bool(demo_ready) and all(seat["params"] == {"gain0": .3}
                                       for seat in dashboard.state.seats.values()),
              repr({key: seat["params"] for key, seat in dashboard.state.seats.items()}))
        check("parameters without defaults remain absent",
              all("trigger" not in seat["params"]
                  for seat in dashboard.state.seats.values()))
        check("old-schema and coincidentally named values are pruned",
              all("gain" not in seat["params"] and "obsolete" not in seat["params"]
                  for seat in dashboard.state.seats.values()))

        for seat in dashboard.state.seats.values():
            seat["params"]["gain0"] = .12
        for device in dashboard.state.devices.values():
            if device.get("virtual"):
                device["params"]["gain0"] = .12
        await dashboard.stage_and_converge("demo", ws)
        same_ready = await wait_for(lambda: len([
            device for device in dashboard.state.devices.values()
            if device.get("virtual") and device.get("declared")]) == 2)
        check("same-name Set preserves current values",
              bool(same_ready) and all(seat["params"] == {"gain0": .12}
                                       for seat in dashboard.state.seats.values()))

        await dashboard.stage_and_converge("bonks", ws)
        bonks_ready = await wait_for(lambda: len([
            device for device in dashboard.state.devices.values()
            if device.get("virtual")
            and [declaration.get("name")
                 for declaration in device.get("declared") or ()] == ["gain"]]) == 2)
        check("different-name Set replaces every seat with new defaults",
              bool(bonks_ready) and all(seat["params"] == {"gain": .75}
                                        for seat in dashboard.state.seats.values()),
              repr({key: seat["params"] for key, seat in dashboard.state.seats.items()}))
        check("runtime device mirrors reset with the durable seats",
              all(device["params"] == {"gain": .75}
                  for device in dashboard.state.devices.values()
                  if device.get("virtual")))

        for seat in dashboard.state.seats.values():
            seat["params"]["gain"] = .2
        await dashboard.stage_and_converge("bonks", ws)
        await wait_for(lambda: len([
            device for device in dashboard.state.devices.values()
            if device.get("virtual") and device.get("declared")]) == 2)
        check("same-name restage after editing preserves operator values",
              all(seat["params"] == {"gain": .2}
                  for seat in dashboard.state.seats.values()))

        await dashboard.handle_ws({"type": "revert_fleet_patch", "data": {
            "confirmed": True}}, ws)
        reverted = await wait_for(lambda: dashboard.state.data["fleet_patch"]["name"] == "demo"
                                  and all(seat["params"] == {"gain0": .3}
                                          for seat in dashboard.state.seats.values()))
        check("Revert restores the previous manifest defaults",
              bool(reverted), repr(dashboard.state.data["fleet_patch"]))
    finally:
        await dashboard.stop()


async def main():
    with tempfile.TemporaryDirectory() as temp:
        await integration(temp)
    print(f"\n{9 - len(FAILURES)}/9 passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
