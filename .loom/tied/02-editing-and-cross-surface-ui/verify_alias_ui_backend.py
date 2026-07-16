#!/usr/bin/env python3
"""Focused API and cross-surface source checks for device aliases."""

import asyncio
import os
import pathlib
import sys
import tempfile
from types import SimpleNamespace

sys.dont_write_bytecode = True


def repo_root():
    here = pathlib.Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "dashboard" / "server.py").is_file():
            return candidate
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
sys.path[:0] = [str(ROOT), str(ROOT / "dashboard")]

from dashboard.server import Dashboard


passed = 0


def check(label, condition, detail=""):
    global passed
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    passed += 1
    print(f"PASS {label}")


class FakeWS:
    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)


def args(root):
    return SimpleNamespace(
        state_file=os.path.join(root, "installation.json"), devices_file=None,
        listen_port=0, send_port=0, osc_target="127.0.0.1",
        assets_dir=os.path.join(root, "assets"),
        patches_dir=os.path.join(root, "patches"), public_url=None,
        sim_audio_backend="none", sim_no_engine=True, sim_engine_port_base=26661)


with tempfile.TemporaryDirectory(prefix="bopos-alias-ui-") as temp:
    dashboard = Dashboard(args(temp))
    first_uid, second_uid = "02:00:00:00:00:01", "02:00:00:00:00:02"
    for uid in (first_uid, second_uid):
        dashboard.state.devices[uid] = dashboard.state._runtime_device(uid)
        dashboard.state.ensure_device_alias(uid)
    dashboard.state.save()
    ws = FakeWS()
    dashboard.clients.add(ws)

    asyncio.run(dashboard.handle_ws(
        {"type": "set_device_alias", "data": {"uid": first_uid,
                                                 "alias": "Freda Sparks"}}, ws))
    check("Rename API persists one custom physical alias",
          dashboard.state.alias_for(first_uid) == "Freda Sparks"
          and dashboard.state.device_registry[first_uid]["source"] == "custom")

    ws.messages.clear()
    asyncio.run(dashboard.handle_ws(
        {"type": "set_device_alias", "data": {"uid": second_uid,
                                                 "alias": "freda sparks"}}, ws))
    check("Rename API rejects a concurrent case-insensitive duplicate",
          dashboard.state.alias_for(second_uid) != "freda sparks"
          and any(message.get("type") == "error" for message in ws.messages))

    ws.messages.clear()
    asyncio.run(dashboard.handle_ws(
        {"type": "reset_device_alias", "data": {"uid": first_uid}}, ws))
    check("Reset API restores and broadcasts a generated alias",
          dashboard.state.device_registry[first_uid]["source"] == "generated"
          and any(message.get("type") == "state" for message in ws.messages))

    projected = asyncio.run(dashboard.public_device(dashboard.state.devices[first_uid]))
    check("device projections carry alias while runtime facts remain clean",
          projected["alias"] == dashboard.state.alias_for(first_uid)
          and "alias" not in dashboard.state.devices[first_uid])

dashboard_js = (ROOT / "dashboard/static/js/dashboard.js").read_text()
facilitator_js = (ROOT / "dashboard/static/js/facilitator.js").read_text()
identity_js = (ROOT / "dashboard/static/js/device-identity.js").read_text()
index_html = (ROOT / "dashboard/static/index.html").read_text()
facilitator_html = (ROOT / "dashboard/static/facilitator.html").read_text()

check("both dashboard entrypoints load the one shared identity helper",
      "/js/device-identity.js" in index_html
      and "/js/device-identity.js" in facilitator_html)
check("Devices provides Rename and Reset without editing Seat or hostname",
      'ws.send("set_device_alias"' in dashboard_js
      and 'ws.send("reset_device_alias"' in dashboard_js
      and "never its Seat or hostname" in dashboard_js)
check("Forget confirmation names custom-alias loss",
      "Its custom alias will be deleted." in dashboard_js)
check("Seats and Assets consume the shared alias-first formatter",
      "Identity.full(binding||seat.bound,installation)" in dashboard_js
      and "Identity.full(target.device,installation)" in dashboard_js)
check("bound Dashboard cards keep Seat primary and alias secondary",
      "primary: `${name} · ID ${seat.id}`" in facilitator_js
      and "Identity.primary(d,installation)" in facilitator_js)
check("technical identity retains hostname and UID tail",
      "device?.hostname" in identity_js and "uidTail" in identity_js)

print(f"\n{passed}/10 checks passed")
