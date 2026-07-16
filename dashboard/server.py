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
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

import points
from osc_bridge import FETCH_TIMEOUT_SECONDS, OSCBridge
from state import (InstallationState, observed_active_patch, patch_badge,
                   reconcile_patch_switch_success)

REPO_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)
from python import identity
from python import manifest as patch_manifest


NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
PATCH_TEMPLATE = os.path.join(".templates", "bopos-template.pd")
PATCH_SWITCH_RECEIPT_SECONDS = 8.0
PATCH_SWITCH_RECONCILE_SECONDS = 2.0


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


def directory_manifest(root_dir, name, kind="patch"):
    # the walk/fingerprint itself lives in python/identity.py so nodes report
    # the identical identity; the HTTP-facing name/path guards stay here
    valid_name = (identity.valid_asset_slot(name) if kind == "asset"
                  else NAME_RE.fullmatch(name) is not None)
    if not valid_name:
        raise HTTPException(status_code=404)
    root = os.path.join(root_dir, name)
    if os.path.islink(root) or not os.path.isdir(root):
        raise HTTPException(status_code=404)
    return identity.directory_manifest(root)


def directory_info(root_dir, name, kind):
    root = os.path.join(root_dir, name)
    manifest = directory_manifest(root_dir, name, kind)
    files = manifest["files"]
    modified = os.stat(root).st_mtime
    for item in files:
        modified = max(modified, os.stat(os.path.join(root, item["path"])).st_mtime)
    valid, error, manifest_data = True, None, None
    if kind == "patch":
        manifest_data, error = patch_manifest.load(root)
        valid = error is None
    info = {"kind": kind, "name": name, "files": len(files),
            "bytes": sum(item["size"] for item in files), "modified": modified,
            "fingerprint": identity.manifest_fingerprint(manifest),
            "valid": valid, "error": error}
    if kind == "patch":
        # The manifest editor needs declarations for a catalog selection that
        # is not yet the active edit process. Keep distribution identity and
        # authored manifest data as separate, explicitly named fields.
        info["manifest"] = manifest_data
    return info


def distribution_catalog(assets_dir, patches_dir):
    def entries(root, kind):
        valid_name = identity.valid_asset_slot if kind == "asset" \
            else lambda value: NAME_RE.fullmatch(value) is not None
        names = (name for name in os.listdir(root)
                 if valid_name(name)
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
        self.manifest_lock = asyncio.Lock()
        self.supervisor_generation = 0
        # One managed-audition subprocess owns the loopback command port.  Keep
        # sim_process as the compatibility handle used by the existing focused
        # verifies; supervisor.mode is the authority for what that child means.
        self.state.data["supervisor"] = {"mode": "off"}
        self.state.data["editor"] = {
            "active": False, "status": "off", "patch": None,
            "engine_alive": None, "generation": 0, "params": {},
            "declarations": [], "cues": [], "points": {},
            "point_element": 0, "engine": None,
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
        elif (message_type in {"device_update", "patches", "assets", "report",
                               "params_declaration", "rev"}
              and isinstance(data, dict)):
            # OSC callbacks cross into the asyncio loop through queued tasks.
            # A supervisor stop can remove its virtual device before an older
            # task runs; never let that stale payload recreate a browser card.
            device = self.state.devices.get(data.get("uid"))
            if device is None:
                return
            uid = data["uid"]
            data = await self.public_device(device)
            # Enrichment resolves the live host catalog asynchronously. The
            # supervisor may remove (or replace) this uid while it awaits.
            if self.state.devices.get(uid) is not device:
                return
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
        await ws.send_json({"type": "venues", "data": {
            "venues": self.state.list_venues(),
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

    async def handle_ws(self, message, ws=None, supervisor_locked=False,
                        manifest_locked=False):
        kind, data = message.get("type"), message.get("data", {})
        uid = data.get("uid")
        fleet_mutations = {
            "set_param", "set_live_param", "replay_live_params", "set_device_mute",
            "action", "identify", "switch_patch", "set_fleet_patch",
            "revert_fleet_patch", "retry_fleet_patch", "add_patch", "pull_patch",
            "send_distribution", "sync_distribution", "drop_distribution",
            "save_preset", "load_preset", "mute_all", "add_seat", "update_seat",
            "reindex_seat", "remove_seat", "bind_seat", "unbind_seat",
            "create_group", "rename_group", "delete_group", "set_seat_groups",
            "forget_device", "forget_offline_unbound", "set_room", "set_points",
            "set_point", "clear_point", "save_venue", "load_venue",
        }
        if self.supervisor_mode == "edit" and kind in fleet_mutations:
            await self.ws_error(ws, "Fleet controls are unavailable while patch edit mode owns the audio relay.")
            return
        if kind in {"save_patch_manifest", "create_patch"} and not manifest_locked:
            async with self.manifest_lock:
                return await self.handle_ws(
                    message, ws, supervisor_locked=supervisor_locked,
                    manifest_locked=True)
        if kind in fleet_mutations and not supervisor_locked:
            async with self.supervisor_lock:
                return await self.handle_ws(message, ws, supervisor_locked=True)
        if kind == "set_param":
            name, value = str(data.get("name", "")), data.get("value")
            selector = "all" if data.get("broadcast") or uid == "all" else self.selector(uid)
            if not name or selector is None:
                return
            targets = self.state.devices.values() if selector == "all" else [self.state.devices[uid]]
            if selector == "all":
                for seat in self.state.seats.values():
                    seat["params"][name] = value
            for device in targets:
                device["params"][name] = value
                seat = self.state.seat_for_uid(device["uid"])
                if seat is not None and selector != "all":
                    seat["params"][name] = value
            self.osc.set_param(selector, name, value)
            self.state.save_debounced()
            for device in targets:
                await self.broadcast("device_update", device)
        elif kind == "set_live_param":
            scope = str(data.get("scope", ""))
            declaration = self.live_param_declaration(data.get("name"))
            cleaned = self.clean_editor_value(declaration, data.get("value"))
            seats, selector = self.live_param_target(scope, data.get("id"))
            if declaration is None or cleaned is None or seats is None:
                await self.ws_error(ws, "That live parameter or target is unavailable.")
                return
            identity = declaration["identity"]
            previous = {str(seat["id"]): dict(seat.get("params", {})) for seat in seats}
            previous_devices = {uid: dict(device.get("params", {}))
                                for uid, device in self.state.devices.items()}
            for seat in seats:
                seat.setdefault("params", {})[identity] = cleaned
                device = self.state.devices.get(seat.get("bound"))
                if device is not None:
                    device.setdefault("params", {})[identity] = cleaned
                for virtual in self.state.devices.values():
                    if (virtual.get("virtual")
                            and str(virtual.get("seat_id")) == str(seat["id"])):
                        virtual.setdefault("params", {})[identity] = cleaned
            try:
                self.state.save()
            except (OSError, TypeError, ValueError):
                for seat in seats:
                    seat["params"] = previous[str(seat["id"])]
                for uid, params in previous_devices.items():
                    if uid in self.state.devices:
                        self.state.devices[uid]["params"] = params
                await self.ws_error(ws, "Could not save the live parameter; no command was sent.")
                return
            self.osc.set_param(selector, identity, cleaned)
            await self.broadcast("state", self.state.public())
        elif kind == "replay_live_params":
            scope = str(data.get("scope", ""))
            if scope == "all":
                seats = sorted(self.state.seats.values(), key=lambda item: item["id"])
            elif scope == "seat":
                seat_id = self.state.clean_seat_id(data.get("id"))
                seat = self.state.seats.get(str(seat_id))
                seats = [seat] if seat is not None else None
            else:
                seats = None
            declarations = self.live_control_declarations()
            if seats is None or not declarations:
                await self.ws_error(ws, "That live replay target is unavailable.")
                return
            # Replay is deliberately numeric even for All: this is an ordered
            # refresh of each Seat snapshot, not a fleet-wide value overwrite.
            for seat in seats:
                for declaration in declarations:
                    identity = declaration["identity"]
                    if identity in seat.get("params", {}):
                        self.osc.set_param(int(seat["id"]), identity,
                                           seat["params"][identity])
        elif kind == "set_device_mute":
            mute_uid = str(data.get("uid", ""))
            raw_value = data.get("value")
            device = self.state.devices.get(mute_uid)
            if (raw_value not in (0, 1) or isinstance(raw_value, bool)
                    or device is None or device.get("virtual")
                    or mute_uid not in self.state.device_registry):
                await self.ws_error(ws, "That physical device mute target is unavailable.")
                return
            if self.state.data.get("muted"):
                await self.ws_error(ws, "Individual device mute is unavailable during fleet mute.")
                return
            desired = bool(raw_value)
            if not self.state.set_device_muted(mute_uid, desired):
                await self.ws_error(ws, "Could not save device mute; no command was sent.")
                return
            device["mute_pending_at"] = time.time()
            self.osc.set_device_mute(mute_uid, desired)
            await self.broadcast("device_update", device)
        elif kind == "set_editor_param":
            name, value = str(data.get("name", "")), data.get("value")
            editor = self.state.data["editor"]
            declaration = next((item for item in editor.get("declarations", ())
                                if patch_manifest.qualify_param(item) == name), None)
            cleaned = self.clean_editor_value(declaration, value)
            if self.supervisor_mode == "edit" and cleaned is not None:
                editor.setdefault("params", {})[name] = cleaned
                self.osc.set_param(0, name, cleaned)
                await self.broadcast("state", self.state.public())
        elif kind == "set_editor_point":
            if self.supervisor_mode != "edit":
                return
            point = points.sanitize_point(data.get("point"))
            if point is None:
                return
            editor = self.state.data["editor"]
            editor.setdefault("points", {})[point["id"]] = point
            self.osc.send_editor_point(point)
            await self.broadcast("editor_points", {"points": editor["points"]})
        elif kind == "clear_editor_point":
            if self.supervisor_mode != "edit":
                return
            try:
                point_id = int(data.get("id"))
            except (TypeError, ValueError):
                return
            editor = self.state.data["editor"]
            if editor.setdefault("points", {}).pop(point_id, None) is not None:
                self.osc.clear_editor_point(point_id)
                await self.broadcast("editor_points", {"points": editor["points"]})
        elif kind == "set_editor_point_element":
            if self.supervisor_mode != "edit":
                return
            try:
                element = int(data.get("element"))
            except (TypeError, ValueError):
                return
            if element not in (0, 1):
                return
            editor = self.state.data["editor"]
            editor["point_element"] = element
            self.osc.send_editor_element(element)
            await self.broadcast("editor_point_element", {"element": element})
        elif kind == "save_patch_manifest":
            await self.save_patch_manifest(data, ws)
        elif kind == "create_patch":
            await self.create_patch(data, ws)
        elif kind == "action" and data.get("verb") in {"reboot", "shutdown", "restart-engine",
                                                       "updatebopos"}:
            if uid == "all":
                self.osc.action("all", data["verb"])
            elif uid in self.state.devices and not self.state.devices[uid].get("virtual"):
                self.osc.uid_action(uid, data["verb"])
        elif kind == "identify":
            if uid in self.state.devices:
                self.osc.uid_action(uid, "identify")
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
                    device = self.begin_patch_switch(device_uid, name)
                    if device is not None:
                        await self.broadcast("device_update", device)
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
            requested = []
            if kind == "send_distribution":
                item_kind = str(data.get("kind", ""))
                name = str(data.get("name", ""))
                if item_kind == "asset" and not self.single_asset_target(uid):
                    await self.ws_error(
                        ws, "Assets require one online, assigned physical device target.")
                    return
                requested = [item for group in catalog.values() for item in group
                             if item["kind"] == item_kind and item["name"] == name
                             and (item["kind"] != "patch" or item["valid"])]
            else:
                # Fleet asset sync moved to the separately gated rollout work.
                requested = [item for item in catalog["patches"] if item["valid"]]
            targets = self.distribution_targets(uid)
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
                    encoded_name = urllib.parse.quote(item["name"], safe="")
                    uri = f"{base_urls[device_uid]}/{path}/{encoded_name}/.manifest.json"
                    self.osc.fetch(device_uid, uri, slot, item["fingerprint"])
        elif kind == "drop_distribution":
            item_kind, name = str(data.get("kind", "")), str(data.get("name", ""))
            if item_kind == "asset" and not self.single_asset_target(uid):
                await self.ws_error(
                    ws, "Assets require one online, assigned physical device target.")
                return
            targets = self.distribution_targets(uid)
            valid_name = (identity.valid_asset_slot(name) if item_kind == "asset"
                          else NAME_RE.fullmatch(name) is not None)
            if valid_name and item_kind in ("patch", "asset"):
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
            cue_id = data.get("cue_id") if isinstance(data.get("cue_id"), str) else ""
            if patch_manifest.CUE_ID.fullmatch(cue_id) is None:
                if ws is not None:
                    await ws.send_json({"type": "error", "data": {
                        "message": "cue name: use 1–64 characters without newlines"}})
                return
            try:
                lead_ms = int(data.get("lead_ms", 500))
            except (TypeError, ValueError):
                lead_ms = 500
            shared_time_ns, lead_ms = self.osc.fire_cue(cue_id, lead_ms)
            await self.broadcast("cue_scheduled", {"cue_id": cue_id,
                                                    "shared_time_ns": str(shared_time_ns),
                                                    "lead_ms": lead_ms})
        elif kind == "fire_editor_cue":
            if self.supervisor_mode != "edit":
                return
            cue_id = data.get("cue_id") if isinstance(data.get("cue_id"), str) else ""
            if patch_manifest.CUE_ID.fullmatch(cue_id) is None:
                await self.ws_error(ws, "cue name: use 1–64 characters without newlines")
                return
            shared_time_ns = self.osc.fire_cue_now(cue_id)
            await self.broadcast("editor_cue_fired", {
                "cue_id": cue_id, "shared_time_ns": str(shared_time_ns)})
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
            active = self.active_param_identities()
            for seat_id, params in values.items():
                seat = self.state.seats.get(str(seat_id))
                if seat is None or not isinstance(params, dict):
                    continue
                applicable = {str(name): value for name, value in params.items()
                              if str(name) in active}
                seat["params"].update(applicable)
                device = self.state.devices.get(seat.get("bound"))
                if device is None:
                    continue
                for name, value in applicable.items():
                    device["params"][str(name)] = value
                    self.osc.set_param(int(seat["id"]), str(name), value)
                await self.broadcast("device_update", device)
            self.osc.send_master()
            self.state.save_debounced()
        elif kind == "mute_all":
            value = int(bool(data.get("value")))
            self.state.data["muted"] = bool(value)
            self.osc.os_command("all", "mute", [value])
            # Reassert each exact physical-box layer after the session overlay.
            # In particular, releasing MUTE ALL must not unmute a box whose
            # durable UID intent remains true.
            for device_uid, device in self.state.devices.items():
                if not device.get("virtual") and device.get("online"):
                    self.osc.set_device_mute(
                        device_uid, self.state.device_muted_for(device_uid))
            await self.broadcast("mute_all", {"value": value})
        elif kind == "set_simulation":
            async with self.supervisor_lock:
                if bool(data.get("active")):
                    if (ws is not None and self.supervisor_mode != "simulate"
                            and data.get("confirmed") is not True):
                        message = ("Leaving Patch edit for Simulation requires confirmation."
                                   if self.supervisor_mode == "edit" else
                                   "Starting Simulation requires confirmation.")
                        await self.ws_error(ws, message)
                        return
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
                if (active and ws is not None and self.supervisor_mode != "edit"
                        and data.get("confirmed") is not True):
                    message = ("Leaving a running simulation for Patch edit requires confirmation."
                               if self.supervisor_mode == "simulate" else
                               "Starting Patch edit requires confirmation.")
                    await self.ws_error(ws, message)
                    return
                if (not active and ws is not None and self.supervisor_mode == "edit"
                        and data.get("confirmed") is not True):
                    await self.ws_error(ws, "Stopping Patch edit requires confirmation.")
                    return
                if active:
                    await self.start_edit(str(data.get("patch", "")).strip() or None)
                else:
                    await self.stop_edit()
            await self.broadcast("state", self.state.public())
        elif kind in ("restart_edit", "relaunch_edit"):
            async with self.supervisor_lock:
                if self.supervisor_mode == "edit":
                    editor = self.state.data["editor"]
                    patch_name = editor.get("patch")
                    scratch_points = dict(editor.get("points", {}))
                    point_element = int(editor.get("point_element", 0))
                    await self.stop_edit()
                    await self.start_edit(patch_name)
                    # Restart/relaunch is still the same edit session. Restore
                    # its scratch geometry to the fresh relay without making
                    # it durable or joining installation-wide point state.
                    if self.supervisor_mode == "edit":
                        self.state.data["editor"]["points"] = scratch_points
                        self.state.data["editor"]["point_element"] = point_element
                        self.osc.send_editor_element(point_element)
                        for point in scratch_points.values():
                            self.osc.send_editor_point(point)
                    await self.broadcast("state", self.state.public())
        elif kind == "add_seat":
            seat_id = self.state.clean_seat_id(data.get("id"))
            if seat_id is None:
                await self.ws_error(ws, "Seat IDs must be non-negative integers.")
                return
            seat = self.state.clean_seat({"id": seat_id, "name": data.get("name", ""),
                "positions": data.get("positions", []), "patch": data.get("patch", "demo-pd"),
                "params": data.get("params", {}), "bound": None})
            if seat is None:
                await self.ws_error(ws, "Seat IDs must be non-negative integers.")
                return
            if str(seat_id) in self.state.seats:
                await self.ws_error(ws, f"Seat ID {seat_id} already exists.")
                return
            self.state.seats[str(seat_id)] = seat
            self.state.save_debounced()
            if self.state.data["simulation"].get("active"):
                if self.supervisor_mode == "simulate":
                    await self.restart_simulation()
            await self.broadcast("state", self.state.public())
        elif kind == "create_group":
            group, error = self.state.create_group(data.get("name", ""))
            if error:
                await self.ws_error(ws, error)
                return
            await self.broadcast("state", self.state.public())
        elif kind == "rename_group":
            group, error = self.state.rename_group(data.get("id"), data.get("name", ""))
            if error:
                await self.ws_error(ws, error)
                return
            await self.broadcast("state", self.state.public())
        elif kind == "delete_group":
            group_id = self.state.clean_group_id(data.get("id"))
            affected = [seat for seat in self.state.seats.values()
                        if group_id in seat.get("groups", [])]
            _removed, error = self.state.delete_group(group_id)
            if error:
                await self.ws_error(ws, error)
                return
            for seat in affected:
                self.sync_seat_groups(seat)
            await self.broadcast("state", self.state.public())
        elif kind == "set_seat_groups":
            seat, error = self.state.set_seat_groups(data.get("id"), data.get("groups"))
            if error:
                await self.ws_error(ws, error)
                return
            self.sync_seat_groups(seat)
            await self.broadcast("state", self.state.public())
        elif kind == "reindex_seat":
            seat, error = self.state.reindex_seat(data.get("id"), data.get("new_id"))
            if error:
                await self.ws_error(ws, error)
                return
            self.assign_seat(seat)
            if self.state.data["simulation"].get("active"):
                if self.supervisor_mode == "simulate":
                    await self.restart_simulation()
            await self.broadcast("state", self.state.public())
            await self.broadcast("seat_reindexed", {
                "old_id": data.get("id"), "new_id": seat["id"]})
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
            seat = self.state.seats.get(str(data.get("id")))
            if seat is None:
                return
            removed_uid = seat.get("bound")
            if not await self.revoke_online(removed_uid, ws, "remove this Seat"):
                return
            if self.state.delete_seat(seat["id"]) is None:
                self.replay_current_assignments()
                await self.ws_error(ws, "Could not remove the Seat; no changes were made.")
                return
            self.mark_offline_revoking(removed_uid)
            if self.state.data["simulation"].get("active"):
                if self.supervisor_mode == "simulate":
                    await self.restart_simulation()
            await self.broadcast("state", self.state.public())
        elif kind == "bind_seat":
            seat = self.state.seats.get(str(data.get("id")))
            bind_uid = str(data.get("uid", ""))
            device = self.state.devices.get(bind_uid)
            if (seat is None or device is None or device.get("virtual")
                    or device.get("revoking_assignment")):
                await self.ws_error(ws, "Choose a physical device for this Seat.")
                return
            source = next((other for other in self.state.seats.values()
                           if other.get("bound") == bind_uid and other is not seat), None)
            displaced_uid = seat.get("bound") if seat.get("bound") != bind_uid else None
            if (source is not None or displaced_uid) and data.get("confirmed") is not True:
                await self.ws_error(
                    ws, "This assignment replaces an existing Seat binding; confirm it first.")
                return
            for changed_uid in (displaced_uid, bind_uid if source is not None else None):
                if not await self.revoke_online(changed_uid, ws, "replace this Seat binding"):
                    self.replay_current_assignments()
                    return
            previous = {key: item.get("bound") for key, item in self.state.seats.items()}
            if source is not None:
                source["bound"] = None
            seat["bound"] = bind_uid
            try:
                self.state.save()
            except (OSError, TypeError, ValueError):
                for key, bound_uid in previous.items():
                    self.state.seats[key]["bound"] = bound_uid
                self.replay_current_assignments()
                await self.ws_error(ws, "Could not save the Seat assignment; no changes were made.")
                return
            self.mark_offline_revoking(displaced_uid)
            if source is not None:
                self.mark_offline_revoking(bind_uid)
            self.assign_seat(seat)
            await self.broadcast("state", self.state.public())
        elif kind == "unbind_seat":
            seat = self.state.seats.get(str(data.get("id")))
            if seat is not None:
                if not await self.revoke_online(seat.get("bound"), ws, "unassign this Seat"):
                    return
                previous = seat.get("bound")
                seat["bound"] = None
                try:
                    self.state.save()
                except (OSError, TypeError, ValueError):
                    seat["bound"] = previous
                    self.replay_current_assignments()
                    await self.ws_error(ws, "Could not save the unassignment; no changes were made.")
                    return
                self.mark_offline_revoking(previous)
                await self.broadcast("state", self.state.public())
        elif kind == "set_device_alias":
            alias, error = self.state.set_device_alias(
                str(data.get("uid", "")), data.get("alias"))
            if error:
                await self.ws_error(ws, error)
                return
            await self.broadcast("state", self.state.public())
        elif kind == "reset_device_alias":
            alias, error = self.state.reset_device_alias(str(data.get("uid", "")))
            if error:
                await self.ws_error(ws, error)
                return
            await self.broadcast("state", self.state.public())
        elif kind == "forget_device":
            forget_uid = str(data.get("uid", ""))
            device = self.state.devices.get(forget_uid)
            seat = next((item for item in self.state.seats.values()
                         if item.get("bound") == forget_uid), None)
            if seat is not None:
                await self.ws_error(
                    ws, f"Unassign {self.state.alias_for(forget_uid) or forget_uid} before forgetting it.")
                return
            registry_entry = self.state.remove_device_alias(forget_uid)
            removed_device = self.state.devices.pop(forget_uid, None)
            if removed_device is not None or registry_entry is not None:
                try:
                    self.state.save()
                except (OSError, TypeError, ValueError):
                    if removed_device is not None:
                        self.state.devices[forget_uid] = device
                    if registry_entry is not None:
                        self.state.device_registry[forget_uid] = registry_entry
                    await self.ws_error(ws, "Could not forget the device; no changes were made.")
                    return
                await self.broadcast("state", self.state.public())
        elif kind == "forget_offline_unbound":
            bound = {seat.get("bound") for seat in self.state.seats.values()}
            removed = {}
            for device_uid in list(self.state.devices):
                if device_uid not in bound and not self.state.devices[device_uid].get("online"):
                    removed[device_uid] = (self.state.devices.pop(device_uid),
                                           self.state.remove_device_alias(device_uid))
            if removed:
                try:
                    self.state.save()
                except (OSError, TypeError, ValueError):
                    for device_uid, (device, registry_entry) in removed.items():
                        self.state.devices[device_uid] = device
                        if registry_entry is not None:
                            self.state.device_registry[device_uid] = registry_entry
                    await self.ws_error(ws, "Could not forget offline devices; no changes were made.")
                    return
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
                try:
                    self.state.save_venue(name)
                except (OSError, TypeError, ValueError):
                    await self.ws_error(ws, "The venue snapshot could not be saved.")
                    return
                await self.broadcast("venues", {"venues": self.state.list_venues(),
                                                "current": self.state.data.get("name")})
        elif kind == "load_venue":
            name = str(data.get("name", "")).strip()
            loaded, desired_seats = (self.state.read_venue(name)
                                     if name in self.state.list_venues() else (None, None))
            if loaded is None:
                await self.ws_error(ws, "That venue could not be loaded.")
                return
            desired = {seat.get("bound"): seat["id"] for seat in desired_seats.values()
                       if seat.get("bound")}
            changed_uids = []
            for current in self.state.seats.values():
                current_uid = current.get("bound")
                if current_uid and desired.get(current_uid) != current["id"]:
                    changed_uids.append(current_uid)
                    if not await self.revoke_online(current_uid, ws, "load this venue"):
                        self.replay_current_assignments()
                        return
            if self.state.load_venue(name, (loaded, desired_seats)):
                for changed_uid in changed_uids:
                    self.mark_offline_revoking(changed_uid)
                if (self.state.data["simulation"].get("active")
                        and self.supervisor_mode == "simulate"):
                    await self.restart_simulation()
                for seat in self.state.seats.values():
                    if seat.get("bound"):
                        self.assign_seat(seat)
                        self.osc.request(seat["bound"], "patches")
                self.osc.send_audition_listener()
                await self.broadcast("state", self.state.public())
                await self.broadcast("venue_rebind", self.state.last_venue_rebind)
                await self.broadcast("venues", {"venues": self.state.list_venues(),
                                                "current": self.state.data.get("name")})
            else:
                self.replay_current_assignments()
                await self.ws_error(ws, "The venue could not be saved as current; no dashboard state changed.")
        elif kind == "list_venues":
            await self.broadcast("venues", {"venues": self.state.list_venues(),
                                            "current": self.state.data.get("name")})
        elif kind == "request_params":
            self.osc.request(uid, "params")
        elif kind == "request_report":
            self.osc.request(uid, "report")

    async def revoke_online(self, uid, ws, action):
        """Make an online physical node acknowledge id=-1 before mutation."""
        device = self.state.devices.get(uid)
        if not uid or device is None or device.get("virtual") or not device.get("online"):
            return True
        if await self.osc.unassign(uid):
            return True
        await self.ws_error(
            ws, f"Could not {action}: {device.get('hostname') or uid} did not acknowledge unassignment. No dashboard state changed.")
        return False

    def mark_offline_revoking(self, uid):
        device = self.state.devices.get(uid)
        if (uid and device is not None and not device.get("virtual")
                and not device.get("online")):
            device["revoking_assignment"] = True

    def selector(self, uid):
        seat = self.state.seat_for_uid(uid)
        return int(seat["id"]) if seat else None

    def distribution_targets(self, uid):
        if uid == "all":
            return [device_uid for device_uid, device in self.state.devices.items()
                    if self.state.seat_for_uid(device_uid) and device.get("online")]
        return ([uid] if uid in self.state.devices and self.selector(uid) is not None
                and self.state.devices[uid].get("online") else [])

    def single_asset_target(self, uid):
        """Assets 11b permits exactly one assigned online physical node."""
        device = self.state.devices.get(uid)
        return bool(device and device.get("online") and not device.get("virtual")
                    and self.selector(uid) is not None)

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
        manifest, error = patch_manifest.load(
            os.path.join(self.patches_dir, item["name"]))
        if manifest is None:  # catalog validity and this load should agree
            raise ValueError(error)
        declarations = list(manifest.get("params", ()))
        identities = [patch_manifest.qualify_param(item) for item in declarations]
        defaults = {patch_manifest.qualify_param(declaration): declaration["default"]
                    for declaration in declarations if "default" in declaration}
        self.state.reconcile_fleet_params(item["name"], identities, defaults)
        return self.state.stage_fleet_patch(item["name"], item["fingerprint"])

    def active_param_identities(self):
        """Return the staged manifest identities; fail closed when unavailable."""
        patch_name = self.state.data.get("params_patch")
        if not patch_name:
            return set()
        manifest, _error = patch_manifest.load(os.path.join(self.patches_dir, patch_name))
        if manifest is None:
            return set()
        return {patch_manifest.qualify_param(item)
                for item in manifest.get("params", ())}

    def live_control_declarations(self):
        """Validated promoted schema for Seat-owned live controls."""
        patch_name = self.state.data.get("params_patch")
        if not patch_name:
            return []
        manifest, _error = patch_manifest.load(os.path.join(self.patches_dir, patch_name))
        if manifest is None:
            return []
        declarations = []
        for item in manifest.get("params", ()):
            if item.get("facilitator") is True:
                projected = dict(item)
                projected["identity"] = patch_manifest.qualify_param(item)
                declarations.append(projected)
        return declarations

    def live_param_declaration(self, identity):
        if not isinstance(identity, str):
            return None
        return next((item for item in self.live_control_declarations()
                     if item["identity"] == identity), None)

    def live_param_target(self, scope, target_id):
        if scope == "all":
            return list(self.state.seats.values()), "all"
        if scope == "seat":
            seat_id = self.state.clean_seat_id(target_id)
            seat = self.state.seats.get(str(seat_id))
            return ([seat], seat_id) if seat is not None else (None, None)
        if scope == "group":
            group_id = self.state.clean_group_id(target_id)
            if group_id is None or str(group_id) not in self.state.data.get("groups", {}):
                return None, None
            seats = self.state.seats_for_group(group_id)
            return (seats, f"g{group_id}") if seats else (None, None)
        return None, None

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
        # Alias is a projection of the durable host registry, never a runtime
        # device fact or node-provided identity.
        public["alias"] = (None if device.get("virtual")
                           else self.state.alias_for(device.get("uid")))
        if device.get("virtual"):
            public.update(device_muted=False, mute_observed=None,
                          effective_muted=None, mute_status="unconfirmed")
        else:
            desired_mute = self.state.device_muted_for(device.get("uid"))
            observed = device.get("mute_observed")
            pending_at = device.get("mute_pending_at")
            if isinstance(observed, bool) and observed == desired_mute:
                mute_status = "current"
            elif pending_at is not None and time.time() - pending_at < 5.0:
                mute_status = "pending"
            else:
                mute_status = "unconfirmed"
            public.update(device_muted=desired_mute, mute_observed=observed,
                          effective_muted=device.get("effective_muted"),
                          mute_status=mute_status)
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
        declarations = self.live_control_declarations()
        public["live_controls"] = {
            "patch": self.state.data.get("params_patch") if declarations else None,
            "declarations": declarations,
        }
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

    def patch_path(self, name):
        """Return a catalog child path, or None for unsafe names/symlinks."""
        if NAME_RE.fullmatch(name or "") is None:
            return None
        path = os.path.join(self.patches_dir, name)
        if os.path.islink(path):
            return None
        return path

    async def save_patch_manifest(self, data, ws):
        """Validate and atomically save the editable manifest fields."""
        name = str(data.get("patch", "")).strip()
        patch_path = self.patch_path(name)
        editor = self.state.data["editor"]
        if (patch_path is None or not os.path.isdir(patch_path)
                or self.supervisor_mode != "edit" or editor.get("patch") != name):
            await self.ws_error(ws, "The selected patch is not active in edit mode.")
            return
        current, error = patch_manifest.load(patch_path)
        if current is None:
            await self.ws_error(ws, f"Cannot edit patch {name!r}: {error}")
            return

        params, cues = data.get("params"), data.get("cues")
        if not isinstance(params, list) or not isinstance(cues, list):
            await self.ws_error(ws, "Manifest params and cues must be lists.")
            return
        candidate = dict(current)
        candidate["params"] = params
        candidate["cues"] = cues
        saved, error = await asyncio.to_thread(
            patch_manifest.write_atomic, patch_path, candidate)
        if saved is None:
            await self.ws_error(ws, f"Manifest not saved: {error}")
            return

        old_names = [patch_manifest.qualify_param(item)
                     for item in current.get("params", ())]
        new_names = [patch_manifest.qualify_param(item)
                     for item in saved.get("params", ())]
        removed = [item for item in old_names if item not in new_names]
        added = [item for item in new_names if item not in old_names]
        rename_candidates = [
            {"from": old, "to": new}
            for old, new in zip(removed, added)
        ]
        warning = None
        if removed:
            warning = ("Parameter identities were moved, renamed, or removed. "
                       "Update matching engine routes manually: "
                       + ", ".join("/p/" + item for item in removed))

        # Manifest saves are live declaration changes, never engine restarts.
        previous_values = editor.get("params", {})
        declarations = list(saved.get("params", ()))
        editor["declarations"] = declarations
        editor["cues"] = list(saved.get("cues", ()))
        editor["params"] = {
            patch_manifest.qualify_param(declaration): previous_values.get(
                patch_manifest.qualify_param(declaration), declaration.get("default", ""))
            for declaration in declarations
        }
        response = {
            "patch": name,
            "params": declarations,
            "cues": editor["cues"],
            "removed_params": removed,
            "added_params": added,
            "rename_candidates": rename_candidates,
            "pd_receive_warning": warning,
        }
        if ws is not None:
            await ws.send_json({"type": "manifest_saved", "data": response})
        await self.broadcast("distribution", await self.catalog())
        await self.broadcast("state", self.state.public())

    async def create_patch(self, data, ws):
        """Create a minimal patch and copy Bob's immutable stub when present."""
        name = str(data.get("name", "")).strip()
        patch_path = self.patch_path(name)
        if patch_path is None:
            await self.ws_error(ws, "Patch name: start with a letter or digit; then use letters, digits, dot, _ or -.")
            return
        try:
            os.mkdir(patch_path)
        except FileExistsError:
            await self.ws_error(ws, f"Patch {name!r} already exists.")
            return
        except OSError as error:
            await self.ws_error(ws, f"Could not create patch {name!r}: {error}")
            return

        template = os.path.join(self.patches_dir, PATCH_TEMPLATE)
        entrypoint = os.path.join(patch_path, "main.pd")
        template_copied = os.path.isfile(template) and not os.path.islink(template)
        try:
            if template_copied:
                await asyncio.to_thread(shutil.copyfile, template, entrypoint)
            minimal = {"engine": "pd", "entrypoint": "main.pd", "params": [],
                       "cues": [], "caps": [], "slots": []}
            saved, error = await asyncio.to_thread(
                patch_manifest.write_atomic, patch_path, minimal, template_copied)
            if saved is None:
                raise OSError(error)
        except OSError as error:
            for partial in (entrypoint,
                            os.path.join(patch_path, patch_manifest.MANIFEST_NAME)):
                try:
                    os.unlink(partial)
                except OSError:
                    pass
            try:
                os.rmdir(patch_path)
            except OSError:
                pass
            await self.ws_error(ws, f"Could not create patch {name!r}: {error}")
            return

        status = ("Ready: copied .templates/bopos-template.pd verbatim."
                  if template_copied else
                  "Manifest created; add main.pd or restore the PD template before launch.")
        response = {"patch": name, "template_copied": template_copied,
                    "status": status}
        if ws is not None:
            await ws.send_json({"type": "patch_created", "data": response})
        await self.broadcast("distribution", await self.catalog())

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
        # Attempts belong to the desired patch generation. Clearing their
        # identity tokens also makes their untracked monitor tasks exit.
        for device in self.state.devices.values():
            device["patch_switch"] = None
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
            device = self.begin_patch_switch(uid, name)
            if device is not None:
                switched.append(device)
        for device in switched:
            await self.broadcast("device_update", device)

        # Force a final badge broadcast for nodes that did not converge too.
        for uid in targets:
            if uid in self.state.devices:
                await self.broadcast("device_update", self.state.devices[uid])

    async def retry_fleet_patch(self, uid, ws):
        if uid not in self.distribution_targets(uid):
            device = self.state.devices.get(uid)
            if device and not self.state.seat_for_uid(uid):
                await self.ws_error(
                    ws, "Assign this device to a Seat before syncing the fleet patch; "
                    "OSC v1.5 cannot uniquely target unbound content operations.")
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
        if badge in ("failed", "timeout"):
            # Retry is a new attempt. Re-derive from observation so the row
            # chooses re-switch vs re-fetch honestly.
            self.state.devices[uid]["patch_switch"] = None
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
        device = self.begin_patch_switch(uid, name)
        if device is not None:
            await self.broadcast("device_update", device)

    def begin_patch_switch(self, uid, name):
        device = self.state.devices.get(uid)
        selector = self.selector(uid)
        if not device or not device.get("online") or selector is None:
            return None
        attempt = {"patch": name, "at": time.time(), "status": "switching"}
        device["patch_switch"] = attempt
        device["active_asset_slots"] = None
        self.osc.os_command(selector, "patch", [name])
        self.spawn(self.monitor_patch_switch(uid, attempt))
        return device

    async def monitor_patch_switch(self, uid, attempt):
        """Bound a switch even when its UDP receipt is lost or ambiguous."""
        await asyncio.sleep(PATCH_SWITCH_RECEIPT_SECONDS)
        device = self.state.devices.get(uid)
        if not device or device.get("patch_switch") is not attempt:
            return
        if reconcile_patch_switch_success(device):
            await self.broadcast("device_update", device)
            return
        attempt["status"] = "reconciling"
        await self.broadcast("device_update", device)
        for member in ("patches", "params", "report"):
            self.osc.request(uid, member)
        await asyncio.sleep(PATCH_SWITCH_RECONCILE_SECONDS)
        device = self.state.devices.get(uid)
        if not device or device.get("patch_switch") is not attempt:
            return
        if reconcile_patch_switch_success(device):
            await self.broadcast("device_update", device)
            return
        active = observed_active_patch(device)
        if active:
            attempt.update(status="failed",
                           reason=f"Observed active patch {active!r}, not {attempt['patch']!r}.")
        else:
            attempt.update(status="timeout",
                           reason="Timed out without an attributable patch observation.")
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

    def assign_seat(self, seat):
        uid = seat.get("bound")
        if uid in self.state.devices:
            self.osc.assign(uid, seat["id"], seat["name"], seat["positions"])
            self.state.devices[uid]["params"] = dict(seat["params"])
            if self.state.devices[uid].get("online"):
                self.state.devices[uid]["revoking_assignment"] = False
        if self.state.data["simulation"].get("active"):
            for virtual_uid, device in self.state.devices.items():
                if (device.get("virtual")
                        and str(device.get("seat_id")) == str(seat["id"])):
                    self.osc.assign(virtual_uid, seat["id"], seat["name"], seat["positions"])

    def sync_seat_groups(self, seat):
        uid = seat.get("bound")
        if uid in self.state.devices and hasattr(self.osc, "send_groups"):
            self.osc.send_groups(uid)
        for virtual_uid, device in self.state.devices.items():
            if (hasattr(self.osc, "send_groups") and device.get("virtual")
                    and str(device.get("seat_id")) == str(seat["id"])):
                self.osc.send_groups(virtual_uid)

    def replay_current_assignments(self):
        for seat in self.state.seats.values():
            uid = seat.get("bound")
            if uid in self.state.devices and self.state.devices[uid].get("online"):
                self.assign_seat(seat)

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

    def restore_live_state(self):
        """Retarget and replay dashboard-owned state after private audition."""
        self.osc.set_target(self.performance_target)
        for seat in self.state.seats.values():
            if seat.get("bound") in self.state.devices:
                self.assign_seat(seat)
        self.osc.send_master()
        self.osc.os_command("all", "mute", [
            int(bool(self.state.data.get("muted", False)))])
        for uid, device in self.state.devices.items():
            if not device.get("virtual") and device.get("online"):
                self.osc.set_device_mute(uid, self.state.device_muted_for(uid))

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
        self.restore_live_state()
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
            self.restore_live_state()
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
            self.restore_live_state()

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
        # Simulation is a private runtime target. Choosing its fallback must
        # never stage or change the desired Live fleet deployment.
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
        self.restore_live_state()

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
                      params={patch_manifest.qualify_param(item): item.get("default", "")
                              for item in declarations},
                      declarations=declarations,
                      cues=list(manifest.get("cues", ())),
                      points={},
                      point_element=0,
                      engine=manifest.get("engine"))
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
        editor.update(active=False, status="off", engine_alive=None, points={})
        self.set_supervisor_mode("off")
        self.restore_live_state()

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
        return JSONResponse(directory_manifest(assets, slot, "asset"))

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
