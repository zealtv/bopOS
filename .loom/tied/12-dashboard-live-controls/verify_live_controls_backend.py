#!/usr/bin/env python3
"""Focused Dashboard state/wire verification for live controls and device mute."""

import asyncio
import copy
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "dashboard" / "server.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
sys.path[:0] = [str(ROOT), str(ROOT / "dashboard")]

from dashboard.server import Dashboard  # noqa: E402
from dashboard.state import InstallationState  # noqa: E402
from python import manifest  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


class FakeWS:
    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)


class Wire:
    def __init__(self, state):
        self.state = state
        self.frames = []
        self.snapshots = []

    def set_param(self, selector, name, value):
        self.frames.append(("param", selector, name, value))
        self.snapshots.append({key: copy.deepcopy(seat["params"])
                               for key, seat in self.state.seats.items()})

    def set_device_mute(self, uid, value):
        self.frames.append(("device-mute", uid, int(bool(value))))

    def os_command(self, selector, member, args=()):
        self.frames.append(("os", selector, member, list(args)))


def args(root):
    return SimpleNamespace(
        host="127.0.0.1", port=0,
        state_file=str(Path(root, "installation.json")), devices_file=None,
        listen_port=0, send_port=0, osc_target="127.0.0.1",
        assets_dir=str(Path(root, "assets")), patches_dir=str(Path(root, "patches")),
        public_url=None, sim_audio_backend="none", sim_no_engine=True,
        sim_engine_port_base=26661,
    )


def write_patch(root):
    patch = Path(root, "patches", "alpha")
    patch.mkdir(parents=True)
    (patch / "main.bin").write_bytes(b"live-controls-verifier")
    params = [
        {"path": ["synth", "voice"], "name": "density", "type": "f",
         "min": 0, "max": 1, "default": .25, "dashboard": True},
        {"name": "gate", "type": "i", "min": 0, "max": 1,
         "default": 0, "dashboard": True},
        {"path": ["labels"], "name": "word", "type": "s",
         "dashboard": True},
        {"name": "hidden", "type": "f", "min": 0, "max": 1,
         "default": .4, "dashboard": False},
    ]
    saved, error = manifest.write_atomic(patch, {
        "engine": "test", "entrypoint": "main.bin", "params": params,
        "cues": [], "caps": [], "slots": [],
    })
    if saved is None:
        raise RuntimeError(error)
    return patch, params


def seat(seat_id, groups, bound):
    return {"id": seat_id, "name": f"Seat {seat_id}",
            "positions": [[float(seat_id), 1.0]], "groups": list(groups),
            "params": {}, "bound": bound, "patch": "alpha"}


async def verify():
    with tempfile.TemporaryDirectory(prefix="bopos-live-controls-") as root:
        Path(root, "assets").mkdir()
        patch, declarations = write_patch(root)
        Path(root, "installation.json").write_text(json.dumps({
            "schema": 1, "name": "Live verifier", "groups": {
                "3": {"id": 3, "name": "Front"},
                "4": {"id": 4, "name": "Empty"},
            }, "next_group_id": 5, "seats": {
                "7": seat(7, [3], "node-a"),
                "2": seat(2, [3], None),
                "10": seat(10, [], "node-b"),
            },
        }), encoding="utf-8")
        dashboard = Dashboard(args(root))
        node_a = dashboard.state.ensure("node-a")
        node_a.update(id=7, ip="10.0.0.7", online=True)
        node_b = dashboard.state.ensure("node-b")
        node_b.update(id=10, ip="10.0.0.10", online=False)
        dashboard.stage_catalog_patch({"name": "alpha", "fingerprint": "a" * 64})
        wire = Wire(dashboard.state)
        dashboard.osc.set_param = wire.set_param
        dashboard.osc.set_device_mute = wire.set_device_mute
        dashboard.osc.os_command = wire.os_command

        public = await dashboard.public_state()
        identities = [item["identity"] for item in public["live_controls"]["declarations"]]
        check("public live schema keeps promoted flat and nested identities",
              public["live_controls"]["patch"] == "alpha"
              and identities == ["synth/voice/density", "gate", "labels/word"],
              repr(public["live_controls"]))
        check("unpromoted declaration is fail-closed from live controls",
              "hidden" not in identities)

        wire.frames.clear()
        await dashboard.handle_ws({"type": "set_live_param", "data": {
            "scope": "all", "name": "synth/voice/density", "value": .6,
        }})
        check("All updates every Seat including offline and unbound",
              all(item["params"]["synth/voice/density"] == .6
                  for item in dashboard.state.seats.values()))
        check("All emits one qualified datagram", wire.frames == [
            ("param", "all", "synth/voice/density", .6)], repr(wire.frames))

        wire.frames.clear()
        wire.snapshots.clear()
        await dashboard.handle_ws({"type": "set_live_param", "data": {
            "scope": "group", "id": 3, "name": "gate", "value": 1,
        }})
        check("Group updates online and offline/unbound members only",
              dashboard.state.seats["7"]["params"]["gate"] == 1
              and dashboard.state.seats["2"]["params"]["gate"] == 1
              and dashboard.state.seats["10"]["params"]["gate"] == 0)
        check("Group durable mirrors precede exactly one group datagram",
              wire.frames == [("param", "g3", "gate", 1)]
              and wire.snapshots[0]["7"]["gate"] == 1
              and wire.snapshots[0]["2"]["gate"] == 1,
              repr((wire.frames, wire.snapshots)))

        wire.frames.clear()
        await dashboard.handle_ws({"type": "set_live_param", "data": {
            "scope": "seat", "id": 10, "name": "labels/word", "value": "bright",
        }})
        check("Seat write uses stable numeric Seat selector while offline",
              dashboard.state.seats["10"]["params"]["labels/word"] == "bright"
              and wire.frames == [("param", 10, "labels/word", "bright")],
              repr(wire.frames))

        before = copy.deepcopy(dashboard.state.seats)
        wire.frames.clear()
        ws = FakeWS()
        invalid = [
            {"scope": "seat", "id": 7, "name": "synth/voice/density", "value": 2},
            {"scope": "seat", "id": 7, "name": "gate", "value": .5},
            {"scope": "seat", "id": 7, "name": "labels/word", "value": 3},
            {"scope": "seat", "id": 7, "name": "hidden", "value": .2},
            {"scope": "device", "id": 7, "name": "gate", "value": 0},
        ]
        for payload in invalid:
            await dashboard.handle_ws({"type": "set_live_param", "data": payload}, ws)
        check("type/range/promotion/target validation rejects all invalid writes",
              dashboard.state.seats == before and not wire.frames
              and len(ws.messages) == len(invalid), repr((wire.frames, ws.messages)))

        original_save = dashboard.state.save
        dashboard.state.save = lambda: (_ for _ in ()).throw(OSError("disk full"))
        wire.frames.clear()
        ws = FakeWS()
        await dashboard.handle_ws({"type": "set_live_param", "data": {
            "scope": "group", "id": 3, "name": "gate", "value": 0,
        }}, ws)
        dashboard.state.save = original_save
        check("failed durable Group update rolls back before wire send",
              dashboard.state.seats["7"]["params"]["gate"] == 1
              and dashboard.state.seats["2"]["params"]["gate"] == 1
              and not wire.frames and bool(ws.messages))

        # Give each Seat distinct snapshots, then prove replay order and purity.
        for index, item in enumerate(sorted(dashboard.state.seats.values(),
                                            key=lambda value: value["id"])):
            item["params"].update({"synth/voice/density": .1 + index / 10,
                                   "gate": index % 2, "labels/word": f"s{item['id']}"})
        snapshot = copy.deepcopy(dashboard.state.seats)
        master, fleet_muted = dashboard.state.data["master"], dashboard.state.data["muted"]
        wire.frames.clear()
        await dashboard.handle_ws({"type": "replay_live_params", "data": {
            "scope": "all",
        }})
        expected = []
        for item in sorted(snapshot.values(), key=lambda value: value["id"]):
            for identity in identities:
                expected.append(("param", item["id"], identity, item["params"][identity]))
        check("All Send all is stable Seat-id then declaration order", wire.frames == expected,
              repr(wire.frames))
        check("Send all is idempotent and does not touch state/master/mute",
              dashboard.state.seats == snapshot
              and dashboard.state.data["master"] == master
              and dashboard.state.data["muted"] == fleet_muted)
        wire.frames.clear()
        await dashboard.handle_ws({"type": "replay_live_params", "data": {
            "scope": "seat", "id": 7,
        }})
        check("Seat Send all replays only its promoted snapshot",
              wire.frames == [("param", 7, identity, snapshot["7"]["params"][identity])
                              for identity in identities], repr(wire.frames))

        manifest_path = patch / "bopos.patch.json"
        valid_text = manifest_path.read_text(encoding="utf-8")
        manifest_path.write_text('{"engine":"test","entrypoint":"main.bin","params":"bad"}',
                                 encoding="utf-8")
        public = await dashboard.public_state()
        wire.frames.clear()
        await dashboard.handle_ws({"type": "set_live_param", "data": {
            "scope": "all", "name": "gate", "value": 0,
        }})
        check("invalid live manifest fails the entire promoted surface closed",
              public["live_controls"] == {"patch": None, "declarations": []}
              and not wire.frames, repr(public["live_controls"]))
        manifest_path.write_text(valid_text, encoding="utf-8")

        wire.frames.clear()
        await dashboard.handle_ws({"type": "set_device_mute", "data": {
            "uid": "node-a", "value": 1,
        }})
        pending = await dashboard.public_device(node_a)
        check("device mute persists desired UID intent before exact wire command",
              dashboard.state.device_registry["node-a"]["device_muted"] is True
              and wire.frames == [("device-mute", "node-a", 1)]
              and pending["mute_status"] == "pending", repr((wire.frames, pending)))
        dashboard.osc.handle("/os/mute", ["node-a", 1, 1], "10.0.0.7")
        current = await dashboard.public_device(node_a)
        check("attributable mute receipt converges desired and effective state",
              current["mute_status"] == "current"
              and current["mute_observed"] is True
              and current["effective_muted"] is True, repr(current))
        node_b["mute_pending_at"] = time.time() - 10
        old_node = await dashboard.public_device(node_b)
        check("old node without receipt remains honestly unconfirmed",
              old_node["mute_status"] == "unconfirmed", repr(old_node))

        dashboard.state.data["muted"] = True
        wire.frames.clear()
        ws = FakeWS()
        await dashboard.handle_ws({"type": "set_device_mute", "data": {
            "uid": "node-a", "value": 0,
        }}, ws)
        check("fleet safety overlay blocks individual mute mutation",
              dashboard.state.device_muted_for("node-a") is True
              and not wire.frames and bool(ws.messages))
        dashboard.state.data["muted"] = True
        wire.frames.clear()
        await dashboard.handle_ws({"type": "mute_all", "data": {"value": 0}})
        check("fleet release reasserts persistent per-UID state",
              wire.frames[:2] == [("os", "all", "mute", [0]),
                                  ("device-mute", "node-a", 1)], repr(wire.frames))

        dashboard.state.save()
        reloaded = InstallationState(str(Path(root, "installation.json")))
        check("host-global device mute survives restart",
              reloaded.device_muted_for("node-a") is True)

        # Forget is a genuine registry deletion, so the mute intent cannot return.
        dashboard.state.seats["7"]["bound"] = None
        dashboard.state.save()
        await dashboard.handle_ws({"type": "forget_device", "data": {"uid": "node-a"}})
        check("Forget deletes alias and persistent mute intent together",
              "node-a" not in dashboard.state.devices
              and "node-a" not in dashboard.state.device_registry)

        dashboard.osc.close()
        await dashboard.state.close()


def main():
    asyncio.run(verify())
    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
