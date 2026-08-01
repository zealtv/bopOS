#!/usr/bin/env python3
"""Focused browser-free verification for the device alias foundation."""

import asyncio
import json
import os
import pathlib
import re
import sys
import tempfile
from types import SimpleNamespace

sys.dont_write_bytecode = True


def repo_root():
    here = pathlib.Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "dashboard" / "server.py").is_file():
            return candidate
    raise RuntimeError("cannot locate bopOS repository")


ROOT = repo_root()
sys.path[:0] = [str(ROOT), str(ROOT / "dashboard")]

from dashboard import device_aliases
from dashboard.server import Dashboard
from dashboard.state import InstallationState


passes = 0


def check(label, condition, detail=""):
    global passes
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    passes += 1
    print(f"PASS {label}")


class FakeWS:
    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)


def dashboard_args(root):
    return SimpleNamespace(
        state_file=os.path.join(root, "installation.json"), devices_file=None,
        listen_port=0, send_port=0, osc_target="127.0.0.1",
        assets_dir=os.path.join(root, "assets"),
        patches_dir=os.path.join(root, "patches"), public_url=None,
        sim_audio_backend="none", sim_no_engine=True,
        sim_engine_port_base=26661,
    )


check("Freda Sparks anchors two complete 64-word lists",
      len(device_aliases.GIVEN_NAMES) == 64
      and len(device_aliases.CHARACTER_WORDS) == 64
      and device_aliases.GIVEN_NAMES[0] == "Freda"
      and device_aliases.CHARACTER_WORDS[0] == "Sparks")
all_words = device_aliases.GIVEN_NAMES + device_aliases.CHARACTER_WORDS
check("curated words are unique short ASCII alphabetic tokens",
      len({word.casefold() for word in device_aliases.GIVEN_NAMES}) == 64
      and len({word.casefold() for word in device_aliases.CHARACTER_WORDS}) == 64
      and all(re.fullmatch(r"[A-Za-z]{2,12}", word) for word in all_words))
vectors = {
    "2c:cf:67:b3:0a:58": ("Niko Cloud", "Ines Neon"),
    "02:00:00:00:00:01": ("Nia Gold", "Zain Rocket"),
    "machine-alpha": ("Nia Quartz", "Lani Sugar"),
}
check("generator v1 is pinned by candidate and probe vectors",
      all((device_aliases.candidate(uid, 0), device_aliases.candidate(uid, 1)) == expected
          for uid, expected in vectors.items()))

uid = "2c:cf:67:b3:0a:58"
first = device_aliases.candidate(uid)
registry = {"collision-owner": {"alias": first, "source": "generated", "generator": 1}}
allocated = device_aliases.allocate(uid, registry)
check("collision probing preserves the existing owner and selects the next pair",
      registry["collision-owner"]["alias"] == first
      and allocated["alias"] == device_aliases.candidate(uid, 1))

entry, error = device_aliases.set_custom(
    {uid: allocated, "other": {"alias": "Freda Sparks", "source": "custom",
                                "generator": 1}}, uid, "  freda   sparks ")
check("custom aliases normalize whitespace and reject case-insensitive duplicates",
      entry is None and "…other" in error, error)
check("custom aliases require exactly two ASCII alphabetic words",
      all(device_aliases.clean_alias(value) is None for value in
          ("Solo", "Freda-Sparks", "Freda 2", "Fréda Sparks", "Freda Sparks Extra")))

with tempfile.TemporaryDirectory(prefix="bopos-device-alias-") as temp:
    path = os.path.join(temp, "installation.json")
    state = InstallationState(path)
    state.seats["0"] = {"id": 0, "name": "Seat 0", "positions": [],
                        "params": {}, "groups": [], "bound": uid}
    generated, created = state.ensure_device_alias(uid)
    state.save()
    restarted = InstallationState(path)
    check("registry persists independently of the runtime roster",
          created and restarted.alias_for(uid) == generated["alias"]
          and restarted.devices == {})

    legacy_path = pathlib.Path(temp, "older-installation.json")
    older = restarted.durable()
    older.pop("device_registry")
    legacy_path.write_text(json.dumps(older))
    migrated = InstallationState(str(legacy_path))
    check("older bound UIDs gain and persist an alias without a runtime device",
          migrated.alias_for(uid) is not None
          and uid in json.loads(legacy_path.read_text())["device_registry"]
          and migrated.devices == {})

    restarted.save_venue("Gallery")
    venue_path = pathlib.Path(temp, "installations", "Gallery.json")
    venue = json.loads(venue_path.read_text())
    custom, error = restarted.set_device_alias(uid, "Freda Sparks")
    loaded = restarted.load_venue("Gallery")
    check("venue snapshots exclude aliases and venue loads preserve the host registry",
          "device_registry" not in venue and loaded
          and restarted.alias_for(uid) == "Freda Sparks", repr((venue, error)))

    reset, error = restarted.reset_device_alias(uid)
    expected = device_aliases.allocate(uid, restarted.device_registry)
    check("Reset atomically restores this UID's deterministic generated alias",
          error is None and reset["source"] == "generated"
          and reset["alias"] == expected["alias"])

    virtual, created = restarted.ensure_device_alias("audition-0001")
    check("virtual audition identities never enter the physical registry",
          virtual is None and not created and "audition-0001" not in restarted.device_registry)

    device = restarted.ensure(uid)
    device.update(online=False, virtual=False, hostname="bop000")
    check("alias remains separate from Seat, hostname and runtime device facts",
          "alias" not in device and restarted.seats["0"]["name"] == "Seat 0"
          and device["hostname"] == "bop000")

    dashboard = Dashboard(dashboard_args(temp))
    dashboard.state.devices[uid] = dashboard.state._runtime_device(uid)
    dashboard.state.device_registry[uid] = dict(reset)
    dashboard.state.seats["0"] = {"id": 0, "name": "Seat 0", "positions": [],
                                  "params": {}, "groups": [], "bound": uid}
    projected = asyncio.run(dashboard.public_device(dashboard.state.devices[uid]))
    check("public devices expose the registry alias as a derived projection",
          projected["alias"] == reset["alias"]
          and "alias" not in dashboard.state.devices[uid])
    ws = FakeWS()
    asyncio.run(dashboard.handle_ws(
        {"type": "forget_device", "data": {"uid": uid}}, ws,
        supervisor_locked=True))
    check("Forget refuses a bound physical device without mutating its registry",
          uid in dashboard.state.devices and uid in dashboard.state.device_registry
          and any(message.get("type") == "error" for message in ws.messages))

    dashboard.state.seats["0"]["bound"] = None
    ws.messages.clear()
    asyncio.run(dashboard.handle_ws(
        {"type": "forget_device", "data": {"uid": uid}}, ws,
        supervisor_locked=True))
    saved = json.loads(pathlib.Path(path).read_text())
    check("Forget genuinely removes runtime observation and durable registry entry",
          uid not in dashboard.state.devices
          and uid not in dashboard.state.device_registry
          and uid not in saved.get("device_registry", {}))

    bulk_uid = "02:00:00:00:00:99"
    dashboard.state.devices[bulk_uid] = dashboard.state._runtime_device(bulk_uid)
    dashboard.state.device_registry[bulk_uid] = device_aliases.allocate(
        bulk_uid, dashboard.state.device_registry)
    asyncio.run(dashboard.handle_ws(
        {"type": "forget_offline_unbound", "data": {}}, ws,
        supervisor_locked=True))
    check("bulk Forget also removes offline unbound registry entries",
          bulk_uid not in dashboard.state.devices
          and bulk_uid not in dashboard.state.device_registry)

print(f"\n{passes}/16 checks passed")
