#!/usr/bin/env python3
import argparse
import asyncio
import contextlib
import hashlib
import json
import logging
import os
import re
import sys
import time

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

import points
from osc_bridge import OSCBridge
from state import InstallationState

REPO_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)
from python import manifest as patch_manifest


_file_hashes = {}
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
    if NAME_RE.fullmatch(name) is None:
        raise HTTPException(status_code=404)
    root = os.path.join(root_dir, name)
    if os.path.islink(root) or not os.path.isdir(root):
        raise HTTPException(status_code=404)
    files = []
    for directory, dirs, names in os.walk(root):
        dirs[:] = sorted(name for name in dirs
                         if not name.startswith(".")
                         and not os.path.islink(os.path.join(directory, name)))
        for name in sorted(names):
            if (name.startswith(".") or name.endswith(".part")
                    or os.path.islink(os.path.join(directory, name))):
                continue
            path = os.path.join(directory, name)
            stat = os.stat(path)
            signature = (stat.st_ino, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
            cached = _file_hashes.get(path)
            if cached is None or cached[0] != signature:
                hasher = hashlib.sha256()
                with open(path, "rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        hasher.update(chunk)
                digest = hasher.hexdigest()
                _file_hashes[path] = (signature, digest)
            else:
                digest = cached[1]
            files.append({"path": os.path.relpath(path, root).replace(os.sep, "/"),
                          "size": stat.st_size, "sha256": digest})
    files.sort(key=lambda item: item["path"])
    return {"files": files}


def directory_info(root_dir, name, kind):
    root = os.path.join(root_dir, name)
    manifest = directory_manifest(root_dir, name)
    files = manifest["files"]
    modified = os.stat(root).st_mtime
    for item in files:
        modified = max(modified, os.stat(os.path.join(root, item["path"])).st_mtime)
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    valid, error = True, None
    if kind == "patch":
        _loaded, error = patch_manifest.load(root)
        valid = error is None
    return {"kind": kind, "name": name, "files": len(files),
            "bytes": sum(item["size"] for item in files), "modified": modified,
            "fingerprint": hashlib.sha256(canonical).hexdigest(),
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
        for task in self.tasks:
            task.cancel()
        if self.tasks:
            await asyncio.gather(*tuple(self.tasks), return_exceptions=True)
        self.osc.close()
        await self.state.close()

    def queue_broadcast(self, message_type, data):
        asyncio.create_task(self.broadcast(message_type, data))

    async def broadcast(self, message_type, data):
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
        await ws.send_json({"type": "state", "data": self.state.public()})
        await ws.send_json({"type": "distribution", "data": await self.catalog()})
        # A browser reconnect is another full-state convergence edge. Replaying
        # the private listener is idempotent in the audition relay.
        self.osc.send_audition_listener()
        await ws.send_json({"type": "venues", "data": {"venues": self.state.list_venues(),
                                                       "current": self.state.data.get("name")}})
        for device_uid, device in self.state.devices.items():
            if int(device.get("id", -1)) >= 0 and device.get("online"):
                self.osc.request(device_uid, "patches")
        try:
            while True:
                message = await ws.receive_json()
                await self.handle_ws(message, ws)
        except WebSocketDisconnect:
            pass
        finally:
            self.clients.discard(ws)

    async def handle_ws(self, message, ws=None):
        kind, data = message.get("type"), message.get("data", {})
        uid = data.get("uid")
        if kind == "set_param":
            name, value = str(data.get("name", "")), data.get("value")
            selector = "all" if data.get("broadcast") or uid == "all" else self.selector(uid)
            if not name or selector is None:
                return
            targets = self.state.devices.values() if selector == "all" else [self.state.devices[uid]]
            for device in targets:
                device["params"][name] = value
            self.osc.set_param(selector, name, value)
            self.state.save_debounced()
            for device in targets:
                await self.broadcast("device_update", device)
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
                targets = self.distribution_targets(uid)
                if uid == "all":
                    targets = [device_uid for device_uid in targets
                               if self.device_patch(device_uid, name)
                               and self.device_patch(device_uid, name).get("manifest")]
                for device_uid in targets:
                    self.osc.os_command(self.selector(device_uid), "patch", [name])
                    self.spawn(self.refresh_patches_later(device_uid, 2.25))
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
            base_url = self.public_url(ws)
            for device_uid in targets:
                for item in requested:
                    if (item["kind"] == "patch"
                            and self.device_patch(device_uid, item["name"], git=True)):
                        continue
                    path = "patches" if item["kind"] == "patch" else "assets"
                    slot = "patch:" + item["name"] if item["kind"] == "patch" else item["name"]
                    uri = f"{base_url}/{path}/{item['name']}/.manifest.json"
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
            devices = {uid: dict(device["params"])
                       for uid, device in self.state.devices.items()
                       if int(device["id"]) >= 0}
            self.state.data["presets"][name] = {"master": self.state.data.get("master", 1.0),
                                                "devices": devices}
            self.state.save_debounced()
            await self.broadcast("presets", {"names": sorted(self.state.data["presets"])})
        elif kind == "load_preset":
            preset = self.state.data["presets"].get(str(data.get("name", "")))
            if not isinstance(preset, dict):
                return
            master = self.state.clean_master(preset.get("master"))
            self.state.data["master"] = master
            await self.broadcast("master", {"value": master})
            values = preset.get("devices") if isinstance(preset.get("devices"), dict) else {}
            for preset_uid, params in values.items():
                device = self.state.devices.get(preset_uid)
                if device is None or int(device["id"]) < 0 or not isinstance(params, dict):
                    continue
                for name, value in params.items():
                    device["params"][str(name)] = value
                    self.osc.set_param(int(device["id"]), str(name), value)
                await self.broadcast("device_update", device)
            self.osc.send_master()
            self.state.save_debounced()
        elif kind == "mute_all":
            value = int(bool(data.get("value")))
            self.state.data["muted"] = bool(value)
            self.osc.os_command("all", "mute", [value])
            await self.broadcast("mute_all", {"value": value})
        elif kind == "set_position":
            device = self.state.devices.get(uid)
            if not device:
                return
            for key in ("pos1", "pos2"):
                if key not in data:
                    continue
                value = data[key]
                try:
                    device[key] = ([float(value[0]), float(value[1])]
                                   if value is not None else None)
                except (TypeError, ValueError, IndexError):
                    return
            self.state.save_debounced()
            if int(device["id"]) >= 0 and device.get("name"):
                # positions ride /os/assign so the node persists them too
                self.osc.assign(uid, device["id"], device["name"],
                                self.device_elements(device))
            await self.broadcast("device_update", device)
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
        elif kind == "assign_device":
            device = self.state.devices.get(uid)
            error = None
            try:
                new_id = int(data.get("id"))
            except (TypeError, ValueError):
                new_id = -1
            name = re.sub(r"[^\w-]", "-", str(data.get("name", "")).strip())[:32]
            if device is None:
                error = "unknown device"
            elif new_id < 0:
                error = "ID must be a non-negative integer"
            elif not name:
                error = "name required (letters, digits, - or _)"
            else:
                taken = next((other for other_uid, other in self.state.devices.items()
                              if other_uid != uid and int(other["id"]) == new_id), None)
                if taken:
                    error = f"ID {new_id} is already {taken.get('name') or taken['uid']}"
            if error:
                if ws is not None:
                    await ws.send_json({"type": "error", "data": {"message": error}})
                return
            device["id"], device["name"] = new_id, name
            self.osc.assign(uid, new_id, name, self.device_elements(device))
            self.state.save_debounced()
            await self.broadcast("device_update", device)
        elif kind == "save_venue":
            name = re.sub(r"[^\w-]", "-", str(data.get("name", "")).strip())[:48]
            if name:
                self.state.save_venue(name)
                await self.broadcast("venues", {"venues": self.state.list_venues(),
                                                "current": self.state.data.get("name")})
        elif kind == "load_venue":
            name = str(data.get("name", "")).strip()
            if name and self.state.load_venue(name):
                for assigned_uid, device in self.state.devices.items():
                    if int(device["id"]) >= 0 and device.get("name"):
                        self.osc.assign(assigned_uid, device["id"], device["name"],
                                        self.device_elements(device))
                        self.osc.request(assigned_uid, "patches")
                self.osc.send_audition_listener()
                await self.broadcast("state", self.state.public())
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
        device = self.state.devices.get(uid)
        return int(device["id"]) if device else None

    def distribution_targets(self, uid):
        if uid == "all":
            return [device_uid for device_uid, device in self.state.devices.items()
                    if int(device.get("id", -1)) >= 0 and device.get("online")]
        return ([uid] if uid in self.state.devices and self.selector(uid) is not None
                and self.state.devices[uid].get("online") else [])

    def device_patch(self, uid, name, git=None):
        for patch in self.state.devices.get(uid, {}).get("patches") or ():
            if patch.get("name") == name and (git is None or patch.get("git") is git):
                return patch
        return None

    def public_url(self, ws):
        configured = getattr(self.args, "public_url", None)
        if configured:
            return configured.rstrip("/")
        scheme = "https" if ws is not None and ws.url.scheme == "wss" else "http"
        host = ws.headers.get("host") if ws is not None else None
        return f"{scheme}://{host or '127.0.0.1:' + str(self.args.port)}"

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

    @staticmethod
    def device_elements(device):
        # pos1/pos2 are the dashboard's two element slots today; the wire
        # takes true N pairs, pair order = element index (contract sec 5)
        return [pos for pos in (device.get("pos1"), device.get("pos2")) if pos]


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
        assigned = (device for device in dashboard.state.devices.values()
                    if int(device["id"]) >= 0)
        for device in sorted(assigned, key=lambda item: int(item["id"])):
            row = [device["uid"], device.get("name") or "", str(int(device["id"]))]
            if device.get("pos1"):
                row.append(" ".join(format(value, "g") for value in device["pos1"]))
                if device.get("pos2"):
                    row.append(" ".join(format(value, "g") for value in device["pos2"]))
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
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    logging.basicConfig(level=logging.DEBUG if options.debug else logging.INFO)
    uvicorn.run(create_app(options), host=options.host, port=options.port)
