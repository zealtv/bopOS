#!/usr/bin/env python3
"""Focused backend checks for qualified dashboard parameter state."""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "dashboard" / "server.py").is_file():
            return candidate
    raise RuntimeError("cannot locate repository")


REPO = repo_root()
sys.path[:0] = [str(REPO), str(REPO / "dashboard")]

from dashboard.server import Dashboard
from dashboard.state import InstallationState
from python import manifest


FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def declaration(path, name="gain", default=0.0):
    item = {"name": name, "type": "f", "min": 0, "max": 1,
            "default": default}
    if path is not None:
        item["path"] = path
    return item


def write_patch(root, params):
    patch = Path(root, "patches", "alpha")
    patch.mkdir(parents=True, exist_ok=True)
    (patch / "main.bin").write_bytes(b"nested parameter verifier")
    saved, error = manifest.write_atomic(patch, {
        "engine": "test", "entrypoint": "main.bin", "params": params,
        "cues": [], "caps": [], "slots": [],
    })
    if saved is None:
        raise RuntimeError(error)
    return patch


def dashboard_args(root):
    return SimpleNamespace(
        state_file=os.path.join(root, "installation.json"), devices_file=None,
        listen_port=0, send_port=0, osc_target="127.0.0.1",
        assets_dir=os.path.join(root, "assets"),
        patches_dir=os.path.join(root, "patches"), public_url=None,
        sim_audio_backend="none", sim_no_engine=True,
        sim_engine_port_base=26661,
    )


class FakeWS:
    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)

    def last(self, kind):
        return next((item for item in reversed(self.messages)
                     if item.get("type") == kind), None)


async def main_async():
    with tempfile.TemporaryDirectory(prefix="bopos-param-dashboard-") as root:
        os.makedirs(os.path.join(root, "assets"))
        params = [declaration(["instrument", "marimba"], default=.25),
                  declaration(["fx", "reverb"], default=.75),
                  declaration(None, "flat", .5)]
        patch = write_patch(root, params)
        state = {
            "schema": 1, "name": "nested", "seats": {
                "1": {"id": 1, "name": "One", "positions": [[1, 1]],
                      "params": {}, "bound": "node-1"},
                "2": {"id": 2, "name": "Two", "positions": [[2, 2]],
                      "params": {}, "bound": None},
            },
        }
        Path(root, "installation.json").write_text(json.dumps(state))
        dashboard = Dashboard(dashboard_args(root))
        device = dashboard.state.ensure("node-1")
        device.update(id=1, ip="10.0.0.1", online=True)
        sent = []
        dashboard.osc.set_param = lambda selector, name, value: sent.append(
            (selector, name, value))
        dashboard.osc.send_master = lambda selector="all": None

        item = {"name": "alpha", "fingerprint": "a" * 64}
        dashboard.stage_catalog_patch(item)
        expected_defaults = {"instrument/marimba/gain": .25,
                             "fx/reverb/gain": .75, "flat": .5}
        check("fleet schema defaults use qualified keys",
              all(seat["params"] == expected_defaults
                  for seat in dashboard.state.seats.values()))

        await dashboard.handle_ws({"type": "set_param", "data": {
            "uid": "node-1", "name": "instrument/marimba/gain", "value": .4,
        }})
        check("individual nested write updates Seat and OSC identity",
              dashboard.state.seats["1"]["params"]["instrument/marimba/gain"] == .4
              and sent[-1] == (1, "instrument/marimba/gain", .4), repr(sent))
        await dashboard.handle_ws({"type": "set_param", "data": {
            "uid": "all", "name": "fx/reverb/gain", "value": .6,
            "broadcast": True,
        }})
        check("all write updates every Seat including unbound/offline",
              all(seat["params"]["fx/reverb/gain"] == .6
                  for seat in dashboard.state.seats.values())
              and sent[-1] == ("all", "fx/reverb/gain", .6), repr(sent))

        await dashboard.handle_ws({"type": "save_preset", "data": {"name": "nested"}})
        preset = dashboard.state.data["presets"]["nested"]
        preset["seats"]["1"]["removed/stale"] = .9
        dashboard.state.seats["1"]["params"]["instrument/marimba/gain"] = .1
        sent.clear()
        await dashboard.handle_ws({"type": "load_preset", "data": {"name": "nested"}})
        check("preset load restores qualified active identities",
              dashboard.state.seats["1"]["params"]["instrument/marimba/gain"] == .4
              and (1, "instrument/marimba/gain", .4) in sent, repr(sent))
        check("preset load ignores historical undeclared identities",
              "removed/stale" not in dashboard.state.seats["1"]["params"]
              and not any(name == "removed/stale" for _selector, name, _value in sent))
        dashboard.state.save()
        reloaded = InstallationState(os.path.join(root, "installation.json"))
        check("qualified Seat and preset keys survive durable reload",
              reloaded.seats["1"]["params"]["instrument/marimba/gain"] == .4
              and reloaded.data["presets"]["nested"]["seats"]["1"]
                  ["fx/reverb/gain"] == .6)

        # Reconnect/catch-up reuses two duplicate leaves without collision.
        dashboard.state.seats["1"]["params"].update({
            "instrument/marimba/gain": .33, "fx/reverb/gain": .66})
        sent.clear()
        dashboard.osc.handle("/os/params", [json.dumps({"params": params})], "10.0.0.1")
        await asyncio.sleep(0)
        check("reconnect catch-up sends both qualified duplicate leaves",
              (1, "instrument/marimba/gain", .33) in sent
              and (1, "fx/reverb/gain", .66) in sent, repr(sent))

        # Same patch revision: retain unchanged, default added, prune removed.
        revised = [declaration(["instrument", "marimba"], default=.25),
                   declaration(["fx", "delay"], default=.2),
                   declaration(None, "flat", .5)]
        saved, error = manifest.write_atomic(patch, {
            "engine": "test", "entrypoint": "main.bin", "params": revised,
            "cues": [], "caps": [], "slots": [],
        })
        check("same-patch fixture revision validates", saved is not None, str(error))
        dashboard.stage_catalog_patch({"name": "alpha", "fingerprint": "b" * 64})
        seat = dashboard.state.seats["1"]
        check("same-patch revision retains unchanged qualified value",
              seat["params"]["instrument/marimba/gain"] == .33)
        check("same-patch revision defaults added and prunes removed",
              seat["params"]["fx/delay/gain"] == .2
              and "fx/reverb/gain" not in seat["params"], repr(seat["params"]))

        # Editor save treats a path move as remove+add and retains unchanged.
        dashboard.set_supervisor_mode("edit")
        dashboard.state.data["editor"].update(
            active=True, patch="alpha", generation=4, declarations=revised,
            params={"instrument/marimba/gain": .8, "fx/delay/gain": .4,
                    "flat": .7})
        replacement = [declaration(["instrument", "marimba"], default=.25),
                       declaration(["fx", "echo"], default=.9),
                       declaration(None, "flat", .5)]
        ws = FakeWS()
        await dashboard.handle_ws({"type": "save_patch_manifest", "data": {
            "patch": "alpha", "params": replacement, "cues": [],
        }}, ws)
        response = ws.last("manifest_saved")["data"]
        editor = dashboard.state.data["editor"]
        check("path move reports canonical remove plus add",
              response["removed_params"] == ["fx/delay/gain"]
              and response["added_params"] == ["fx/echo/gain"]
              and response["rename_candidates"] == [
                  {"from": "fx/delay/gain", "to": "fx/echo/gain"}]
              and "/p/fx/delay/gain" in response["pd_receive_warning"],
              repr(response))
        check("editor save retains unchanged identities and defaults moved identity",
              editor["params"] == {"instrument/marimba/gain": .8,
                                   "fx/echo/gain": .9, "flat": .7},
              repr(editor["params"]))

        sent.clear()
        await dashboard.handle_ws({"type": "set_editor_param", "data": {
            "name": "fx/echo/gain", "value": .45,
        }})
        check("nested editor send binds the qualified identity",
              editor["params"]["fx/echo/gain"] == .45
              and sent == [(0, "fx/echo/gain", .45)], repr(sent))

        dashboard.osc.close()
        await dashboard.state.close()


def main():
    asyncio.run(main_async())
    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
