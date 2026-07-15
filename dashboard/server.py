#!/usr/bin/env python3
import argparse
import asyncio
import contextlib
import ipaddress
import json
import logging
import math
import os
import re
import socket
import subprocess
import sys
import time

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

import points
from osc_bridge import FETCH_TIMEOUT_SECONDS, OSCBridge
from state import InstallationState, patch_badge

REPO_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)
from python import identity
from python import manifest as patch_manifest


NAME_RE = re.compile(r"[A-Za-z0-9_-]+")


class DistributionStaticFiles(StaticFiles):
    """Serve manifest-listed content without exposing source-control internals."""
    async def get_response(self, path, scope):
        parts = path.replace("\\", "/").split("/")
        if any(part.startswith(".") or part.endswith(".part") for part in parts):
            return PlainTextResponse("Not Found", status_code=404)
        current = self.directory
        for part in parts:
            current = os.path.join(current, part)
            if os.path.islink(current):
                return PlainTextResponse("Not Found", status_code=404)
        return await super().get_response(path, scope)


def directory_manifest(root_dir, name):
    # the walk/fingerprint itself lives in python/identity.py so nodes report
    # the identical identity; the HTTP-facing name/path guards stay here
    if NAME_RE.fullmatch(name) is None:
        raise HTTPException(status_code=404)
    root = os.path.join(root_dir, name)
    if os.path.islink(root) or not os.path.isdir(root):
        raise HTTPException(status_code=404)
    return identity.directory_manifest(root)


def directory_info(root_dir, name, kind):
    root = os.path.join(root_dir, name)
    manifest = directory_manifest(root_dir, name)
    files = manifest["files"]
    modified = os.stat(root).st_mtime
    for item in files:
        modified = max(modified, os.stat(os.path.join(root, item["path"])).st_mtime)
    valid, error = True, None
    if kind == "patch":
        _loaded, error = patch_manifest.load(root)
        valid = error is None
    return {"kind": kind, "name": name, "files": len(files),
            "bytes": sum(item["size"] for item in files), "modified": modified,
            "fingerprint": identity.manifest_fingerprint(manifest),
            "valid": valid, "error": error}


def distribution_catalog(assets_dir, patches_dir):
    def entries(root, kind):
        names = (name for name in os.listdir(root)
                 if NAME_RE.fullmatch(name)
                 and not os.path.islink(os.path.join(root, name))
                 and os.path.isdir(os.path.join(root, name)))
        return [directory_info(root, name, kind) for name in sorted(names)]
    return {"assets": entries(assets_dir, "asset"),
            "patches": entries(patches_dir, "patch")}


class Dashboard:
    def __init__(self, args):
        self.args = args
        self.state = InstallationState(args.state_file, args.devices_file)
        self.clients = set()
        self.osc = OSCBridge(self.state, self.queue_broadcast, args.listen_port,
                             args.send_port, args.osc_target)
        self.tasks = set()
        self.sim_process = None
        self.supervisor_lock = asyncio.Lock()
        self.supervisor_generation = 0
        # One managed-audition subprocess owns the loopback command port.  Keep
        # sim_process as the compatibility handle used by the existing focused
        # verifies; supervisor.mode is the authority for what that child means.
        self.state.data["supervisor"] = {"mode": "off"}
        self.state.data["editor"] = {
            "active": False, "status": "off", "patch": None,
            "engine_alive": None, "generation": 0, "params": {},
            "declarations": [], "engine": None,
        }
        self.fleet_operation = None
        self.fleet_retries = {}
        self.fleet_generation = 0
        self.performance_target = args.osc_target
        self.assets_dir = os.path.realpath(getattr(args, "assets_dir", os.path.join(REPO_DIR, "assets")))
        self.patches_dir = os.path.realpath(getattr(args, "patches_dir", os.path.join(REPO_DIR, "patches")))
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(self.patches_dir, exist_ok=True)

    async def catalog(self):
        return await asyncio.to_thread(distribution_catalog,
                                       self.assets_dir, self.patches_dir)

    async def start(self):
        await self.osc.start()
        self.osc.send_audition_listener()
        self.spawn(self.offline_sweep())

    def spawn(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def stop(self):
        await self.stop_supervisor()
        for task in self.tasks:
            task.cancel()
        if self.tasks:
            await asyncio.gather(*tuple(self.tasks), return_exceptions=True)
        self.osc.close()
        await self.state.close()

    def queue_broadcast(self, message_type, data):
        asyncio.create_task(self.broadcast(message_type, data))

    async def broadcast(self, message_type, data):
        if message_type == "state":
            data = await self.public_state()
        elif (message_type in {"device_update", "patches", "report",
                               "params_declaration", "rev"}
              and isinstance(data, dict) and data.get("uid") in self.state.devices):
            data = await self.public_device(self.state.devices[data["uid"]])
        elif message_type == "device_offline" and isinstance(data, dict):
            device = self.state.devices.get(data.get("uid"))
            if device is not None:
                data = dict(data)
                data["patch_badge"] = patch_badge(device, await self.live_fleet_patch())
        message = {"type": message_type, "data": data}
        dead = []
        for client in tuple(self.clients):
            try:
                await client.send_json(message)
            except Exception:
                dead.append(client)
        self.clients.difference_update(dead)

    async def offline_sweep(self):
        while True:
            await asyncio.sleep(1)
            epoch = time.time()
            for uid, device in self.state.devices.items():
                if device["online"] and device["last_seen"] and epoch - device["last_seen"] > 30:
                    device["online"] = False
                    await self.broadcast("device_offline", {"uid": uid})

    async def websocket(self, ws):
        await ws.accept()
        self.clients.add(ws)
        await ws.send_json({"type": "state", "data": await self.public_state()})
        await ws.send_json({"type": "distribution", "data": await self.catalog()})
        # A browser reconnect is another full-state convergence edge. Replaying
        # the private listener is idempotent in the audition relay.
        self.osc.send_audition_listener()
        await ws.send_json({"type": "venues", "data": {"venues": self.state.list_venues(),
                                                       "current": self.state.data.get("name")}})
        for device_uid, device in self.state.devices.items():
            if self.state.seat_for_uid(device_uid) and device.get("online"):
                self.osc.request(device_uid, "patches")
        try:
            while True:
                message = await ws.receive_json()
                await self.handle_ws(message, ws)
        except WebSocketDisconnect:
            pass
        finally:
            self.clients.discard(ws)

    async def handle_ws(self, message, ws=None, supervisor_locked=False):
        kind, data = message.get("type"), message.get("data", {})
        uid = data.get("uid")
        fleet_mutations = {
            "set_param", "action", "identify", "switch_patch", "set_fleet_patch",
            "revert_fleet_patch", "retry_fleet_patch", "add_patch", "pull_patch",
            "send_distribution", "sync_distribution", "drop_distribution",
            "save_preset", "load_preset", "mute_all", "add_seat", "update_seat",
            "remove_seat", "bind_seat", "unbind_seat", "forget_device",
            "forget_offline_unbound",
        }
        if self.supervisor_mode == "edit" and kind in fleet_mutations:
            await self.ws_error(ws, "Fleet controls are unavailable while patch edit mode owns the audio relay.")
            return
        if kind in fleet_mutations and not supervisor_locked:
            async with self.supervisor_lock:
                return await self.handle_ws(message, ws, supervisor_locked=True)
        if kind == "set_param":
            name, value = str(data.get("name", "")), data.get("value")
            selector = "all" if data.get("broadcast") or uid == "all" else self.selector(uid)
            if not name or selector is None:
                return
            targets = self.state.devices.values() if selector == "all" else [self.state.devices[uid]]
            for device in targets:
                device["params"][name] = value
                seat = self.state.seat_for_uid(device["uid"])
                if seat is not None:
                    seat["params"][name] = value
            self.osc.set_param(selector, name, value)
            self.state.save_debounced()
            for device in targets:
                await self.broadcast("device_update", device)
        elif kind == "set_editor_param":
            name, value = str(data.get("name", "")), data.get("value")
            editor = self.state.data["editor"]
            declaration = next((item for item in editor.get("declarations", ())
                                if item.get("name") == name), None)
            cleaned = self.clean_editor_value(declaration, value)
            if (self.supervisor_mode == "edit" and cleaned is not None
                    and re.fullmatch(r"[A-Za-z0-9_-]+", name)):
                editor.setdefault("params", {})[name] = cleaned
                self.osc.set_param(0, name, cleaned)
                await self.broadcast("state", self.state.public())
        elif kind == "action" and data.get("verb") in {"reboot", "shutdown", "restart-engine",
                                                       "updatebopos"}:
            selector = "all" if uid == "all" else self.selector(uid)
            if selector is not None:
                self.osc.action(selector, data["verb"])
        elif kind == "identify":
            # uid-targeted broadcast: an id selector would flash every
            # unassigned box at once (they all sit at -1)
            if uid in self.state.devices:
                self.osc.os_command("all", "identify", [str(uid)])
        elif kind == "switch_patch":
            name = str(data.get("patch", "")).strip()
            if re.fullmatch(r"[\w.-]+", name):
                if self.state.data["simulation"].get("active"):
                    if ws is not None and data.get("confirmed") is not True:
                        await self.ws_error(ws, "Switching the simulated fleet requires confirmation.")
                        return
                    if self.supervisor_mode != "simulate":
                        await self.ws_error(ws, "Simulation ended before the patch switch completed.")
                        return
                    manifest, error = patch_manifest.load(os.path.join(self.patches_dir, name))
                    if manifest is None:
                        await self.ws_error(ws, f"Cannot simulate patch {name!r}: {error}")
                        return
                    item = await self.catalog_patch(name)
                    if item is None:
                        return
                    self.stage_catalog_patch(item)
                    self.state.save_debounced()
                    await self.restart_simulation()
                    await self.broadcast("state", self.state.public())
                    return
                targets = self.distribution_targets(uid)
                if uid == "all":
                    targets = [device_uid for device_uid in targets
                               if self.device_patch(device_uid, name)
                               and self.device_patch(device_uid, name).get("manifest")]
                for device_uid in targets:
                    device = self.state.devices[device_uid]
                    device["patch_switch"] = {"patch": name, "at": time.time()}
                    await self.broadcast("device_update", device)
                    self.osc.os_command(self.selector(device_uid), "patch", [name])
                    self.spawn(self.refresh_patch_state_later(device_uid, 8.0))
        elif kind == "set_fleet_patch":
            if data.get("confirmed") is not True:
                await self.ws_error(ws, "Setting the fleet patch requires confirmation.")
                return
            await self.stage_and_converge(str(data.get("patch", "")).strip(), ws)
        elif kind == "revert_fleet_patch":
            if data.get("confirmed") is not True:
                await self.ws_error(ws, "Reverting the fleet patch requires confirmation.")
                return
            current = self.state.data.get("fleet_patch") or {}
            previous = current.get("previous") or {}
            if not previous.get("name"):
                await self.ws_error(ws, "There is no previous fleet patch to revert to.")
                return
            await self.stage_and_converge(previous["name"], ws)
        elif kind == "retry_fleet_patch":
            await self.retry_fleet_patch(uid, ws)
        elif kind == "add_patch":
            user, repo = str(data.get("user", "")).strip(), str(data.get("repo", "")).strip()
            selector = "all" if uid in (None, "all") else self.selector(uid)
            if selector is not None and re.fullmatch(r"[\w-]+", user) and re.fullmatch(r"[\w.-]+", repo):
                self.osc.os_command(selector, "addpatch", [user, repo])
                for device_uid in self.distribution_targets(uid):
                    self.spawn(self.refresh_patches_later(device_uid, 1.25))
        elif kind == "pull_patch":
            targets = self.distribution_targets(uid)
            for device_uid in targets:
                listing = self.state.devices[device_uid].get("patches") or ()
                if any(patch.get("active") and patch.get("git") for patch in listing):
                    self.osc.os_command(self.selector(device_uid), "pullpatch")
        elif kind == "request_patches":
            if uid in self.state.devices:
                self.osc.request(uid, "patches")
        elif kind in ("send_distribution", "sync_distribution"):
            if self.state.data["simulation"].get("active"):
                if ws is not None:
                    await ws.send_json({"type": "error", "data": {"message":
                        "Simulation uses host patches directly; choose a patch and Switch "
                        "the simulated fleet instead of sending files."}})
                return
            catalog = await self.catalog()
            await self.broadcast("distribution", catalog)
            targets = self.distribution_targets(uid)
            requested = []
            if kind == "send_distribution":
                item_kind = str(data.get("kind", ""))
                name = str(data.get("name", ""))
                requested = [item for group in catalog.values() for item in group
                             if item["kind"] == item_kind and item["name"] == name
                             and (item["kind"] != "patch" or item["valid"])]
            else:
                requested = ([item for item in catalog["patches"] if item["valid"]]
                             + catalog["assets"])
            if (self.requires_active_confirmation(targets, requested)
                    and data.get("confirmed_active") is not True):
                if ws is not None:
                    await ws.send_json({"type": "error", "data": {"message":
                        "Sending an active patch requires stop/restart confirmation."}})
                return
            base_urls = {}
            try:
                for device_uid in targets:
                    base_urls[device_uid] = self.public_url(ws, device_uid)
            except ValueError as error:
                if ws is not None:
                    await ws.send_json({"type": "error", "data": {"message": str(error)}})
                return
            for device_uid in targets:
                for item in requested:
                    if (item["kind"] == "patch"
                            and self.device_patch(device_uid, item["name"], git=True)):
                        continue
                    path = "patches" if item["kind"] == "patch" else "assets"
                    slot = "patch:" + item["name"] if item["kind"] == "patch" else item["name"]
                    uri = f"{base_urls[device_uid]}/{path}/{item['name']}/.manifest.json"
                    self.osc.fetch(device_uid, uri, slot, item["fingerprint"])
        elif kind == "drop_distribution":
            targets = self.distribution_targets(uid)
            item_kind, name = str(data.get("kind", "")), str(data.get("name", ""))
            if NAME_RE.fullmatch(name) and item_kind in ("patch", "asset"):
                verb = "droppatch" if item_kind == "patch" else "dropassets"
                slot = "patch:" + name if item_kind == "patch" else name
                for device_uid in targets:
                    selector = self.selector(device_uid)
                    if selector is not None:
                        self.osc.os_command(selector, verb, [name])
                        device = self.state.devices[device_uid]
                        device.setdefault("distribution", {}).pop(slot, None)
                        device.setdefault("fetch", {}).pop(slot, None)
                        await self.broadcast("device_update", device)
                        if item_kind == "patch":
                            self.spawn(self.refresh_patches_later(device_uid))
                self.state.save_debounced()
        elif kind == "refresh_distribution":
            await self.broadcast("distribution", await self.catalog())
            # Host edits can change the live desired fingerprint without a node
            # event. Re-emit state so per-device badges immediately expose drift.
            await self.broadcast("state", self.state.public())
        elif kind == "set_master":
            master = self.state.clean_master(data.get("value"))
            self.state.data["master"] = master
            self.state.save_debounced()
            self.osc.send_master()
            await self.broadcast("master", {"value": master})
        elif kind == "fire_cue":
            cue_id = str(data.get("cue_id", "")).strip()
            if re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", cue_id) is None:
                if ws is not None:
                    await ws.send_json({"type": "error", "data": {
                        "message": "cue name: use 1–64 letters, digits, dot, colon, _ or -"}})
                return
            try:
                lead_ms = int(data.get("lead_ms", 500))
            except (TypeError, ValueError):
                lead_ms = 500
            shared_time_ns, lead_ms = self.osc.fire_cue(cue_id, lead_ms)
            await self.broadcast("cue_scheduled", {"cue_id": cue_id,
                                                    "shared_time_ns": str(shared_time_ns),
                                                    "lead_ms": lead_ms})
        elif kind == "save_preset":
            name = re.sub(r"[^\w-]", "-", str(data.get("name", "")).strip())[:48]
            if not name:
                return
            # partial state by construction: params + master only, never
            # positions or assignments (facilitator proposal Q5)
            seats = {str(seat["id"]): dict(seat["params"])
                     for seat in self.state.seats.values()}
            self.state.data["presets"][name] = {"master": self.state.data.get("master", 1.0),
                                                "seats": seats}
            self.state.save_debounced()
            await self.broadcast("presets", {"names": sorted(self.state.data["presets"])})
        elif kind == "load_preset":
            preset = self.state.data["presets"].get(str(data.get("name", "")))
            if not isinstance(preset, dict):
                return
            master = self.state.clean_master(preset.get("master"))
            self.state.data["master"] = master
            await self.broadcast("master", {"value": master})
            values = preset.get("seats") if isinstance(preset.get("seats"), dict) else {}
            for seat_id, params in values.items():
                seat = self.state.seats.get(str(seat_id))
                if seat is None or not isinstance(params, dict):
                    continue
                seat["params"].update(params)
                device = self.state.devices.get(seat.get("bound"))
                if device is None:
                    continue
                for name, value in params.items():
                    device["params"][str(name)] = value
                    self.osc.set_param(int(seat["id"]), str(name), value)
                await self.broadcast("device_update", device)
            self.osc.send_master()
            self.state.save_debounced()
        elif kind == "mute_all":
            value = int(bool(data.get("value")))
            self.state.data["muted"] = bool(value)
            self.osc.os_command("all", "mute", [value])
            await self.broadcast("mute_all", {"value": value})
        elif kind == "set_simulation":
            async with self.supervisor_lock:
                if bool(data.get("active")):
                    await self.start_simulation(str(data.get("patch", "")).strip() or None)
                else:
                    if (ws is not None and self.supervisor_mode == "simulate"
                            and data.get("confirmed") is not True):
                        await self.ws_error(
                            ws, "Stopping a running simulation requires confirmation.")
                        return
                    await self.stop_simulation()
            await self.broadcast("state", self.state.public())
        elif kind == "set_edit":
            async with self.supervisor_lock:
                active = bool(data.get("active"))
                if (active and self.supervisor_mode == "simulate"
                        and data.get("confirmed") is not True):
                    await self.ws_error(ws, "Leaving a running simulation for edit mode requires confirmation.")
                    return
                if active:
                    await self.start_edit(str(data.get("patch", "")).strip() or None)
                else:
                    await self.stop_edit()
            await self.broadcast("state", self.state.public())
        elif kind in ("restart_edit", "relaunch_edit"):
            async with self.supervisor_lock:
                if self.supervisor_mode == "edit":
                    patch_name = self.state.data["editor"].get("patch")
                    await self.stop_edit()
                    await self.start_edit(patch_name)
                    await self.broadcast("state", self.state.public())
        elif kind == "add_seat":
            try:
                seat_id = int(data.get("id"))
            except (TypeError, ValueError):
                return
            seat = self.state.clean_seat({"id": seat_id, "name": data.get("name", ""),
                "positions": data.get("positions", []), "patch": data.get("patch", "demo-pd"),
                "params": data.get("params", {}), "bound": None})
            if seat is None or str(seat_id) in self.state.seats:
                return
            self.state.seats[str(seat_id)] = seat
            self.state.save_debounced()
            if self.state.data["simulation"].get("active"):
                if self.supervisor_mode == "simulate":
                    await self.restart_simulation()
            await self.broadcast("state", self.state.public())
        elif kind == "update_seat":
            seat = self.state.seats.get(str(data.get("id")))
            if seat is None:
                return
            candidate = dict(seat)
            for key in ("name", "positions", "patch", "params"):
                if key in data:
                    candidate[key] = data[key]
            cleaned = self.state.clean_seat(candidate)
            if cleaned is None:
                return
            self.state.seats[str(cleaned["id"])] = cleaned
            self.assign_seat(cleaned)
            self.state.save_debounced()
            await self.broadcast("state", self.state.public())
        elif kind == "remove_seat":
            seat = self.state.seats.pop(str(data.get("id")), None)
            if seat is not None:
                self.state.save_debounced()
                if self.state.data["simulation"].get("active"):
                    if self.supervisor_mode == "simulate":
                        await self.restart_simulation()
                await self.broadcast("state", self.state.public())
        elif kind == "bind_seat":
            seat = self.state.seats.get(str(data.get("id")))
            bind_uid = str(data.get("uid", ""))
            if seat is None or bind_uid not in self.state.devices:
                return
            for other in self.state.seats.values():
                if other.get("bound") == bind_uid:
                    other["bound"] = None
            seat["bound"] = bind_uid
            self.assign_seat(seat)
            self.state.save_debounced()
            await self.broadcast("state", self.state.public())
        elif kind == "unbind_seat":
            seat = self.state.seats.get(str(data.get("id")))
            if seat is not None:
                seat["bound"] = None
                self.state.save_debounced()
                await self.broadcast("state", self.state.public())
        elif kind == "forget_device":
            forget_uid = str(data.get("uid", ""))
            for seat in self.state.seats.values():
                if seat.get("bound") == forget_uid:
                    seat["bound"] = None
            if self.state.devices.pop(forget_uid, None) is not None:
                self.state.save_debounced()
                await self.broadcast("state", self.state.public())
        elif kind == "forget_offline_unbound":
            bound = {seat.get("bound") for seat in self.state.seats.values()}
            for device_uid in list(self.state.devices):
                if device_uid not in bound and not self.state.devices[device_uid].get("online"):
                    del self.state.devices[device_uid]
            await self.broadcast("state", self.state.public())
        elif kind == "set_listener":
            listener = self.state.clean_listener(data)
            if listener is None:
                return
            self.state.data["listener"] = listener
            self.state.save_debounced()
            self.osc.send_audition_listener()
            await self.broadcast("listener", listener)
        elif kind == "set_points":
            # full-state authoring surface (contract sec 4.1); geometry only —
            # decomposition is the nodes' job, never composed here (sec 1)
            sanitized = points.sanitize_points(data.get("points"),
                                               self.state.data.get("room"))
            self.osc.set_points(sanitized)
            await self.broadcast("points", {"points": sanitized})
        elif kind == "set_point":
            point = points.sanitize_point(data.get("point"),
                                          self.state.data.get("room"))
            if point is None:
                return
            self.osc.upsert_point(point)
            await self.broadcast("points", {"points": self.state.data["points"]})
        elif kind == "clear_point":
            try:
                point_id = int(data.get("id"))
            except (TypeError, ValueError):
                return
            self.osc.clear_point(point_id)
            await self.broadcast("points", {"points": self.state.data["points"]})
        elif kind == "set_room":
            room = self.state.clean_room(data)
            if room is not None:
                width, depth = room["width"], room["depth"]
                self.state.data["room"] = room
                for point in self.state.data.get("points", {}).values():
                    motion = point.get("motion") or {}
                    if motion.get("type") == "bounce":
                        motion["bounds"] = [width, depth]
                        origin = motion.get("origin") or [point["x"], point["y"]]
                        motion["origin"] = [min(max(float(origin[0]), 0.0), width),
                                            min(max(float(origin[1]), 0.0), depth)]
                if self.state.data.get("points"):
                    self.osc.send_points_frame()
                    await self.broadcast("points", {"points": self.state.data["points"]})
                listener = (self.state.clean_listener(self.state.data.get("listener"))
                            or self.state.default_listener())
                self.state.data["listener"] = listener
                self.osc.send_audition_listener()
                await self.broadcast("listener", listener)
                self.state.save_debounced()
                await self.broadcast("room", self.state.data["room"])
        elif kind == "save_venue":
            name = re.sub(r"[^\w-]", "-", str(data.get("name", "")).strip())[:48]
            if name:
                self.state.save_venue(name)
                await self.broadcast("venues", {"venues": self.state.list_venues(),
                                                "current": self.state.data.get("name")})
        elif kind == "load_venue":
            name = str(data.get("name", "")).strip()
            if name and self.state.load_venue(name):
                for seat in self.state.seats.values():
                    if seat.get("bound"):
                        self.assign_seat(seat)
                        self.osc.request(seat["bound"], "patches")
                self.osc.send_audition_listener()
                await self.broadcast("state", self.state.public())
                await self.broadcast("venue_rebind", self.state.last_venue_rebind)
                await self.broadcast("venues", {"venues": self.state.list_venues(),
                                                "current": self.state.data.get("name")})
        elif kind == "list_venues":
            await self.broadcast("venues", {"venues": self.state.list_venues(),
                                            "current": self.state.data.get("name")})
        elif kind == "request_params":
            self.osc.request(uid, "params")
        elif kind == "request_report":
            self.osc.request(uid, "report")

    def selector(self, uid):
        seat = self.state.seat_for_uid(uid)
        return int(seat["id"]) if seat else None

    def distribution_targets(self, uid):
        if uid == "all":
            return [device_uid for device_uid, device in self.state.devices.items()
                    if self.state.seat_for_uid(device_uid) and device.get("online")]
        return ([uid] if uid in self.state.devices and self.selector(uid) is not None
                and self.state.devices[uid].get("online") else [])

    def device_patch(self, uid, name, git=None):
        for patch in self.state.devices.get(uid, {}).get("patches") or ():
            if patch.get("name") == name and (git is None or patch.get("git") is git):
                return patch
        return None

    async def catalog_patch(self, name):
        if NAME_RE.fullmatch(name or "") is None:
            return None
        catalog = await self.catalog()
        return next((item for item in catalog["patches"]
                     if item["name"] == name and item["valid"]), None)

    def stage_catalog_patch(self, item):
        """Stage one validated catalog patch and apply its fleet schema."""
        current = self.state.data.get("fleet_patch") or {}
        if (current.get("name") != item["name"]
                or self.state.data.get("params_patch") != item["name"]):
            manifest, error = patch_manifest.load(
                os.path.join(self.patches_dir, item["name"]))
            if manifest is None:  # catalog validity and this load should agree
                raise ValueError(error)
            defaults = {declaration["name"]: declaration["default"]
                        for declaration in manifest.get("params", ())
                        if "default" in declaration}
            self.state.reset_fleet_params(item["name"], defaults)
        return self.state.stage_fleet_patch(item["name"], item["fingerprint"])

    async def live_fleet_patch(self):
        staged = self.state.data.get("fleet_patch")
        if not staged:
            return None
        desired = dict(staged)
        item = await self.catalog_patch(desired["name"])
        if item is not None:
            desired["fingerprint"] = item["fingerprint"]
        return desired

    async def public_device(self, device, desired=None):
        desired = desired if desired is not None else await self.live_fleet_patch()
        public = dict(device)
        public["patch_badge"] = patch_badge(device, desired)
        return public

    async def public_state(self):
        desired = await self.live_fleet_patch()
        public = dict(self.state.public())
        # The durable record captures the identity staged by the operator, but
        # host edits make the live catalog identity the desired convergence
        # target.  Expose the same resolved identity used for row badges so UI
        # diagnostics never show an old digest beside an honestly stale row.
        public["fleet_patch"] = desired
        public["devices"] = {uid: await self.public_device(device, desired)
                             for uid, device in self.state.devices.items()}
        editor = dict(self.state.data["editor"])
        editor_device = self.state.devices.get("audition-0001")
        if self.supervisor_mode == "edit" and editor_device is not None:
            editor["engine_alive"] = int(editor_device.get("engine_alive") or 0)
            if editor["engine_alive"] == 0:
                editor["status"] = "engine closed"
        public["editor"] = editor
        public["supervisor"] = {"mode": self.supervisor_mode}
        return public

    @staticmethod
    async def ws_error(ws, message):
        if ws is not None:
            await ws.send_json({"type": "error", "data": {"message": message}})

    @staticmethod
    def clean_editor_value(declaration, value):
        if not isinstance(declaration, dict):
            return None
        kind = declaration.get("type")
        if kind == "s":
            return value if isinstance(value, str) else None
        if kind not in {"f", "i"} or isinstance(value, bool):
            return None
        try:
            cleaned = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(cleaned):
            return None
        if kind == "i":
            if not cleaned.is_integer():
                return None
            cleaned = int(cleaned)
        minimum, maximum = declaration.get("min"), declaration.get("max")
        if minimum is not None and cleaned < minimum:
            return None
        if maximum is not None and cleaned > maximum:
            return None
        return cleaned

    async def stage_and_converge(self, name, ws):
        item = await self.catalog_patch(name)
        if item is None:
            await self.ws_error(ws, f"Cannot set fleet patch {name!r}: no valid host patch.")
            return False
        targets = self.distribution_targets("all")
        base_urls = {}
        if not self.state.data["simulation"].get("active"):
            try:
                base_urls = {uid: self.public_url(ws, uid) for uid in targets}
            except ValueError as error:
                await self.ws_error(ws, str(error))
                return False

        generation = self.supersede_fleet_operation()
        self.stage_catalog_patch(item)
        self.state.save_debounced()
        await self.broadcast("state", self.state.public())
        await self.broadcast("distribution", await self.catalog())
        if generation != self.fleet_generation:
            return False
        if self.state.data["simulation"].get("active"):
            await self.restart_simulation()
            await self.broadcast("state", self.state.public())
            return True

        self.fleet_operation = self.spawn(
            self.converge_fleet_patch(
                name, item["fingerprint"], targets, base_urls, generation))
        return True

    def supersede_fleet_operation(self):
        self.fleet_generation += 1
        if self.fleet_operation is not None and not self.fleet_operation.done():
            self.fleet_operation.cancel()
        self.fleet_operation = None
        for task in self.fleet_retries.values():
            if not task.done():
                task.cancel()
        self.fleet_retries.clear()
        return self.fleet_generation

    async def converge_fleet_patch(self, name, fingerprint, targets, base_urls,
                                   generation):
        """Converge bytes first, then switch every ready online target together."""
        waiting, ready = set(), set()
        slot = "patch:" + name
        for uid in targets:
            if generation != self.fleet_generation:
                return
            device = self.state.devices.get(uid)
            if not device or not device.get("online"):
                continue
            entry = self.device_patch(uid, name)
            # Content convergence and active-patch convergence are separate:
            # an inactive copy with the exact desired fingerprint needs only
            # the fleet switch, not a redundant fetch/restart cycle.
            if (entry and entry.get("manifest")
                    and entry.get("fingerprint") == fingerprint):
                ready.add(uid)
                continue
            if entry and entry.get("git"):
                continue
            uri = f"{base_urls[uid]}/patches/{name}/.manifest.json"
            if (self.osc.fetch(uid, uri, slot, fingerprint)
                    or self.osc.fetch_matches(uid, slot, fingerprint)):
                waiting.add(uid)

        deadline = time.monotonic() + FETCH_TIMEOUT_SECONDS + 1.0
        while (waiting and generation == self.fleet_generation
               and time.monotonic() < deadline):
            for uid in tuple(waiting):
                device = self.state.devices.get(uid)
                if not device or not device.get("online"):
                    waiting.remove(uid)
                    continue
                entry = self.device_patch(uid, name)
                if (entry and entry.get("manifest")
                        and entry.get("fingerprint") == fingerprint):
                    waiting.remove(uid)
                    ready.add(uid)
                elif (device.get("fetch") or {}).get(slot) in ("err", "timeout"):
                    waiting.remove(uid)
            if waiting:
                await asyncio.sleep(0.1)

        if generation != self.fleet_generation:
            return

        # One fleet operation, no staged waves: devices that could not prove the
        # desired bytes retain honest missing/stale/unknown badges.
        switched = []
        for uid in ready:
            if generation != self.fleet_generation:
                return
            device = self.state.devices.get(uid)
            if not device or not device.get("online"):
                continue
            device["patch_switch"] = {"patch": name, "at": time.time()}
            self.osc.os_command(self.selector(uid), "patch", [name])
            self.spawn(self.refresh_patch_state_later(uid, 8.0))
            switched.append(device)
        for device in switched:
            await self.broadcast("device_update", device)

        # Force a final badge broadcast for nodes that did not converge too.
        for uid in targets:
            if uid in self.state.devices:
                await self.broadcast("device_update", self.state.devices[uid])

    async def retry_fleet_patch(self, uid, ws):
        if uid not in self.distribution_targets(uid):
            return
        item = await self.catalog_patch((self.state.data.get("fleet_patch") or {}).get("name"))
        if item is None:
            await self.ws_error(ws, "The desired fleet patch is not available on the host.")
            return
        generation = self.fleet_generation
        # A Set/Revert already owns convergence for the whole fleet. Retrying
        # one row must not cancel or duplicate that coordinator.
        if self.fleet_operation is not None and not self.fleet_operation.done():
            return
        previous_retry = self.fleet_retries.get(uid)
        if previous_retry is not None and not previous_retry.done():
            previous_retry.cancel()
        self.state.stage_fleet_patch(item["name"], item["fingerprint"])
        self.state.save_debounced()
        desired = {"name": item["name"], "fingerprint": item["fingerprint"]}
        badge = patch_badge(self.state.devices[uid], desired)
        if badge == "mismatch":
            await self.switch_fleet_device(uid, item["name"], generation)
        elif badge in ("missing", "stale", "stale_unverified"):
            try:
                base_url = self.public_url(ws, uid)
            except ValueError as error:
                await self.ws_error(ws, str(error))
                return
            self.fleet_retries[uid] = self.spawn(self.converge_fleet_patch(
                item["name"], item["fingerprint"], [uid], {uid: base_url}, generation))
        await self.broadcast("state", self.state.public())

    async def switch_fleet_device(self, uid, name, generation):
        if generation != self.fleet_generation:
            return
        device = self.state.devices.get(uid)
        selector = self.selector(uid)
        if not device or not device.get("online") or selector is None:
            return
        device["patch_switch"] = {"patch": name, "at": time.time()}
        self.osc.os_command(selector, "patch", [name])
        self.spawn(self.refresh_patch_state_later(uid, 8.0))
        await self.broadcast("device_update", device)

    def public_url(self, ws, device_uid=None):
        configured = getattr(self.args, "public_url", None)
        if configured:
            return configured.rstrip("/")
        scheme = "https" if ws is not None and ws.url.scheme == "wss" else "http"
        host = ws.headers.get("host") if ws is not None else None
        request_hostname = ws.url.hostname if ws is not None else None
        loopback = request_hostname in (None, "localhost")
        if request_hostname not in (None, "localhost"):
            try:
                loopback = ipaddress.ip_address(request_hostname).is_loopback
            except ValueError:
                loopback = False
        if not loopback:
            return f"{scheme}://{host}"

        device = self.state.devices.get(device_uid, {})
        target = str(device.get("ip") or "")
        try:
            target_ip = ipaddress.ip_address(target)
        except ValueError as error:
            raise ValueError(
                "Cannot determine a device-reachable patch URL. Reopen the dashboard "
                "using its LAN address or start it with --public-url http://<LAN-IP>:8080."
            ) from error
        if target_ip.is_loopback:
            return f"http://127.0.0.1:{self.args.port}"
        family = socket.AF_INET6 if target_ip.version == 6 else socket.AF_INET
        try:
            with socket.socket(family, socket.SOCK_DGRAM) as route:
                route.connect((target, 9))
                local = route.getsockname()[0]
        except OSError as error:
            raise ValueError(
                f"Cannot find a LAN route to {target}. Start the dashboard with "
                "--public-url http://<LAN-IP>:8080."
            ) from error
        authority = f"[{local}]" if ":" in local else local
        return f"http://{authority}:{self.args.port}"

    def requires_active_confirmation(self, target_uids, items):
        patch_names = {item["name"] for item in items if item["kind"] == "patch"}
        if not patch_names:
            return False
        for uid in target_uids:
            listing = self.state.devices[uid].get("patches")
            if listing is None:
                return True  # fail safe while the node's active patch is unknown
            if any(patch.get("active") and patch.get("name") in patch_names
                   for patch in listing):
                return True
            if (self.state.devices[uid].get("report") or {}).get("patch") in patch_names:
                return True
        return False

    async def refresh_patches_later(self, uid, delay=0.25):
        await asyncio.sleep(delay)
        if uid in self.state.devices:
            self.osc.request(uid, "patches")

    async def refresh_patch_state_later(self, uid, delay=0.25):
        """Fallback refresh when a provisioning receipt is lost on UDP."""
        await asyncio.sleep(delay)
        if uid in self.state.devices:
            for member in ("patches", "params", "report"):
                self.osc.request(uid, member)

    def assign_seat(self, seat):
        uid = seat.get("bound")
        if uid in self.state.devices:
            self.osc.assign(uid, seat["id"], seat["name"], seat["positions"])
            self.state.devices[uid]["params"] = dict(seat["params"])
        if self.state.data["simulation"].get("active"):
            for virtual_uid, device in self.state.devices.items():
                if (device.get("virtual")
                        and str(device.get("seat_id")) == str(seat["id"])):
                    self.osc.assign(virtual_uid, seat["id"], seat["name"], seat["positions"])

    @property
    def supervisor_mode(self):
        return self.state.data.get("supervisor", {}).get("mode", "off")

    def set_supervisor_mode(self, mode):
        if mode not in {"off", "simulate", "edit"}:
            raise ValueError(f"invalid supervisor mode {mode!r}")
        self.state.data["supervisor"] = {"mode": mode}

    async def terminate_supervisor_process(self):
        self.supervisor_generation += 1
        process, self.sim_process = self.sim_process, None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                await asyncio.to_thread(process.wait, 5)
            except subprocess.TimeoutExpired:
                process.kill()
                await asyncio.to_thread(process.wait)

    def clear_audition_devices(self):
        for uid in [uid for uid, device in self.state.devices.items()
                    if device.get("virtual")]:
            del self.state.devices[uid]

    async def supervisor_exited(self, process, mode, generation):
        await asyncio.to_thread(process.wait)
        if self.sim_process is not process or generation != self.supervisor_generation:
            return
        self.sim_process = None
        self.clear_audition_devices()
        if mode == "simulate":
            self.state.data["simulation"].update(active=False, status="stopped unexpectedly")
        else:
            self.state.data["editor"].update(active=False, status="stopped unexpectedly",
                                              engine_alive=None)
        self.set_supervisor_mode("off")
        self.osc.set_target(self.performance_target)
        await self.broadcast("state", self.state.public())

    async def launch_supervisor(self, command, mode):
        self.supervisor_generation += 1
        generation = self.supervisor_generation
        try:
            process = subprocess.Popen(command, cwd=REPO_DIR,
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
        except OSError:
            self.clear_audition_devices()
            self.set_supervisor_mode("off")
            self.osc.set_target(self.performance_target)
            return False
        self.sim_process = process
        self.spawn(self.supervisor_exited(process, mode, generation))
        return True

    async def stop_supervisor(self):
        if self.supervisor_mode == "edit":
            await self.stop_edit()
        elif self.supervisor_mode == "simulate":
            await self.stop_simulation()
        else:
            await self.terminate_supervisor_process()
            self.clear_audition_devices()
            self.osc.set_target(self.performance_target)

    async def restart_simulation(self):
        patch_name = self.state.data["simulation"].get("patch")
        await self.stop_simulation()
        await self.start_simulation(patch_name)

    async def start_simulation(self, patch_name=None):
        if self.supervisor_mode == "edit":
            await self.stop_edit()
        if self.sim_process is not None or not self.state.seats:
            return
        simulation = self.state.data["simulation"]
        catalog = await self.catalog()
        valid_items = [item for item in catalog["patches"] if item["valid"]]
        valid_patches = [item["name"] for item in valid_items]
        explicit_patch = patch_name is not None
        patch_name = patch_name or simulation.get("patch")
        if patch_name not in valid_patches:
            patch_name = "demo-pd" if "demo-pd" in valid_patches else (
                valid_patches[0] if valid_patches else None)
        manifest_path = (os.path.join(self.patches_dir, patch_name, "bopos.patch.json")
                         if patch_name is not None else None)
        if patch_name is None:
            fallback = os.path.join(REPO_DIR, "patches", "demo-pd", "bopos.patch.json")
            loaded, _error = patch_manifest.load(os.path.dirname(fallback))
            if loaded is None:
                simulation.update(active=False, status="no valid host patches")
                return
            patch_name, manifest_path = "demo-pd", fallback
        item = next((item for item in valid_items if item["name"] == patch_name), None)
        if item is not None and not explicit_patch:
            self.stage_catalog_patch(item)
            self.state.save_debounced()
        else:
            simulation["patch"] = patch_name
        simulation.update(active=True, status="starting")
        self.set_supervisor_mode("simulate")
        self.osc.set_target("127.0.0.1")
        command = [sys.executable, os.path.join(REPO_DIR, "tools", "audition.py"),
            "--devices", str(len(self.state.seats)), "--bind", "127.0.0.1",
            "--target", "127.0.0.1", "--cmd-port", str(self.args.send_port),
            "--report-port", str(self.args.listen_port), "--hb-interval", "0.5",
            "--audio-backend", getattr(self.args, "sim_audio_backend", "none"),
            "--engine-port-base", str(getattr(self.args, "sim_engine_port_base", 16661)),
            "--manifest", manifest_path,
            "--patches-dir", self.patches_dir]
        if getattr(self.args, "sim_no_engine", False):
            command.append("--no-engine")
        if not await self.launch_supervisor(command, "simulate"):
            simulation.update(active=False, status="launch failed")
            return
        simulation["status"] = "running"
        self.osc.send_audition_listener()

    async def stop_simulation(self):
        if self.supervisor_mode != "simulate":
            return
        await self.terminate_supervisor_process()
        self.clear_audition_devices()
        self.state.data["simulation"].update(active=False, status="off")
        desired = (self.state.data.get("fleet_patch") or {}).get("name")
        if desired:
            self.state.data["simulation"]["patch"] = desired
        self.set_supervisor_mode("off")
        self.osc.set_target(self.performance_target)
        for seat in self.state.seats.values():
            if seat.get("bound") in self.state.devices:
                self.assign_seat(seat)

    async def start_edit(self, patch_name=None):
        if self.supervisor_mode == "simulate":
            await self.stop_simulation()
        if self.supervisor_mode == "edit":
            current = self.state.data["editor"].get("patch")
            if patch_name in (None, current):
                return
            await self.stop_edit()

        # The edit relay is a single-target ownership boundary.  No delayed
        # fleet fetch/switch task may survive to emit commands after retarget.
        self.supersede_fleet_operation()

        catalog = await self.catalog()
        valid_items = [item for item in catalog["patches"] if item["valid"]]
        names = [item["name"] for item in valid_items]
        if patch_name not in names:
            desired = (self.state.data.get("fleet_patch") or {}).get("name")
            patch_name = desired if desired in names else (
                "demo-pd" if "demo-pd" in names else (names[0] if names else None))
        if patch_name is None:
            self.state.data["editor"].update(active=False,
                                              status="no valid host patches")
            return
        manifest_path = os.path.join(self.patches_dir, patch_name,
                                     patch_manifest.MANIFEST_NAME)
        manifest, error = patch_manifest.load(os.path.dirname(manifest_path))
        if manifest is None:
            self.state.data["editor"].update(active=False, status=error)
            return

        editor = self.state.data["editor"]
        generation = int(editor.get("generation", 0)) + 1
        declarations = list(manifest.get("params", ()))
        editor.clear()
        editor.update(active=True, status="starting", patch=patch_name,
                      engine_alive=None, generation=generation,
                      params={item["name"]: item.get("default", "")
                              for item in declarations},
                      declarations=declarations, engine=manifest.get("engine"))
        self.set_supervisor_mode("edit")
        self.osc.set_target("127.0.0.1")
        command = [sys.executable, os.path.join(REPO_DIR, "tools", "audition.py"),
            "--edit", "--devices", "1", "--id-base", "0",
            "--bind", "127.0.0.1", "--target", "127.0.0.1",
            "--cmd-port", str(self.args.send_port),
            "--report-port", str(self.args.listen_port), "--hb-interval", "0.2",
            "--audio-backend", getattr(self.args, "sim_audio_backend", "none"),
            "--engine-port-base", str(getattr(self.args, "sim_engine_port_base", 16661)),
            "--manifest", manifest_path, "--patches-dir", self.patches_dir]
        if getattr(self.args, "sim_no_engine", False):
            command.append("--no-engine")
        if not await self.launch_supervisor(command, "edit"):
            editor.update(active=False, status="launch failed", engine_alive=None)
            return
        editor["status"] = "running"

    async def stop_edit(self):
        if self.supervisor_mode != "edit":
            return
        await self.terminate_supervisor_process()
        self.clear_audition_devices()
        editor = self.state.data["editor"]
        editor.update(active=False, status="off", engine_alive=None)
        self.set_supervisor_mode("off")
        self.osc.set_target(self.performance_target)
        for seat in self.state.seats.values():
            if seat.get("bound") in self.state.devices:
                self.assign_seat(seat)

    @staticmethod
    def device_elements(device):
        return list(device.get("positions", ()))


def create_app(args):
    dashboard = Dashboard(args)

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        await dashboard.start()
        yield
        await dashboard.stop()

    app = FastAPI(lifespan=lifespan)

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await dashboard.websocket(ws)

    assets, patches = dashboard.assets_dir, dashboard.patches_dir

    @app.get("/bopos.devices")
    async def devices_export():
        # bopos.devices is a seed/export format now, not the source of truth
        lines = ["uid, name, id, pos1, pos2"]
        for seat in sorted(dashboard.state.seats.values(), key=lambda item: item["id"]):
            row = [seat.get("bound") or "", seat.get("name") or "", str(seat["id"])]
            for position in seat.get("positions", [])[:2]:
                row.append(" ".join(format(value, "g") for value in position))
            lines.append(", ".join(row))
        return PlainTextResponse("\n".join(lines) + "\n")

    @app.get("/assets/{slot}/.manifest.json")
    def assets_manifest(slot: str):
        return JSONResponse(directory_manifest(assets, slot))

    @app.get("/patches/{name}/.manifest.json")
    def patches_manifest(name: str):
        return JSONResponse(directory_manifest(patches, name))

    app.mount("/assets", DistributionStaticFiles(directory=assets), name="assets")
    app.mount("/patches", DistributionStaticFiles(directory=patches), name="patches")
    static = os.path.join(os.path.dirname(__file__), "static")

    @app.get("/facilitator")
    async def facilitator_page():
        return FileResponse(os.path.join(static, "facilitator.html"))

    app.mount("/", StaticFiles(directory=static, html=True), name="static")
    return app


def parse_args():
    parser = argparse.ArgumentParser(description="bopOS web dashboard")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--listen-port", type=int, default=5550)
    parser.add_argument("--send-port", type=int, default=6660)
    parser.add_argument("--osc-target", default="255.255.255.255")
    parser.add_argument("--state-file", default=os.path.join(os.path.dirname(__file__), "installation.json"))
    parser.add_argument("--devices-file")
    parser.add_argument("--assets-dir", default=os.path.join(REPO_DIR, "assets"))
    parser.add_argument("--patches-dir", default=os.path.join(REPO_DIR, "patches"))
    parser.add_argument("--public-url", help="dashboard URL nodes use for patch/asset fetches")
    parser.add_argument("--sim-audio-backend", choices=("coreaudio", "jack", "none"),
                        default="coreaudio" if sys.platform == "darwin" else "jack")
    parser.add_argument("--sim-no-engine", action="store_true",
                        help="test simulation lifecycle without launching audio engines")
    parser.add_argument("--sim-engine-port-base", type=int, default=16661,
                        help=argparse.SUPPRESS)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    logging.basicConfig(level=logging.DEBUG if options.debug else logging.INFO)
    uvicorn.run(create_app(options), host=options.host, port=options.port)
