#!/usr/bin/env python3
import argparse
import asyncio
import contextlib
import hashlib
import logging
import os
import re
import time

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

import points
from osc_bridge import OSCBridge
from state import InstallationState


_asset_hashes = {}


def asset_manifest(assets_dir, slot):
    if re.fullmatch(r"[A-Za-z0-9_-]+", slot) is None:
        raise HTTPException(status_code=404)
    root = os.path.join(assets_dir, slot)
    if not os.path.isdir(root):
        raise HTTPException(status_code=404)
    files = []
    for directory, dirs, names in os.walk(root):
        dirs[:] = sorted(name for name in dirs if not name.startswith("."))
        for name in sorted(names):
            if name.startswith(".") or name.endswith(".part"):
                continue
            path = os.path.join(directory, name)
            stat = os.stat(path)
            key = (path, stat.st_mtime_ns, stat.st_size)
            digest = _asset_hashes.get(key)
            if digest is None:
                hasher = hashlib.sha256()
                with open(path, "rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        hasher.update(chunk)
                digest = hasher.hexdigest()
                _asset_hashes[key] = digest
            files.append({"path": os.path.relpath(path, root).replace(os.sep, "/"),
                          "size": stat.st_size, "sha256": digest})
    files.sort(key=lambda item: item["path"])
    return {"files": files}


class Dashboard:
    def __init__(self, args):
        self.args = args
        self.state = InstallationState(args.state_file, args.devices_file)
        self.clients = set()
        self.osc = OSCBridge(self.state, self.queue_broadcast, args.listen_port,
                             args.send_port, args.osc_target)
        self.tasks = set()

    async def start(self):
        await self.osc.start()
        self.tasks.add(asyncio.create_task(self.offline_sweep()))

    async def stop(self):
        for task in self.tasks:
            task.cancel()
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
        await ws.send_json({"type": "venues", "data": {"venues": self.state.list_venues(),
                                                       "current": self.state.data.get("name")}})
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
                                                       "update", "get_samples", "aloha"}:
            selector = "all" if uid == "all" else self.selector(uid)
            if selector is not None:
                self.osc.action(selector, data["verb"])
        elif kind == "identify":
            # uid-targeted broadcast: an id selector would flash every
            # unassigned box at once (they all sit at -1)
            if uid in self.state.devices:
                self.osc.os_command("all", "identify", [str(uid)])
        elif kind == "switch_patch":
            selector = "all" if uid == "all" else self.selector(uid)
            name = str(data.get("patch", "")).strip()
            if selector is not None and re.fullmatch(r"[\w.-]+", name):
                self.osc.os_command(selector, "patch", [name])
        elif kind == "add_patch":
            user, repo = str(data.get("user", "")).strip(), str(data.get("repo", "")).strip()
            selector = "all" if uid in (None, "all") else self.selector(uid)
            if selector is not None and re.fullmatch(r"[\w-]+", user) and re.fullmatch(r"[\w.-]+", repo):
                self.osc.os_command(selector, "addpatch", [user, repo])
        elif kind == "pull_patch":
            selector = "all" if uid == "all" else self.selector(uid)
            if selector is not None:
                self.osc.os_command(selector, "pullpatch")
        elif kind == "set_master":
            master = self.state.clean_master(data.get("value"))
            self.state.data["master"] = master
            self.state.save_debounced()
            self.osc.send_master()
            await self.broadcast("master", {"value": master})
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
            try:
                width, depth = float(data.get("width")), float(data.get("depth"))
            except (TypeError, ValueError):
                return
            if 0 < width <= 1000 and 0 < depth <= 1000:
                self.state.data["room"] = {"width": width, "depth": depth, "units": "m"}
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

    assets = os.path.realpath(getattr(args, "assets_dir",
                                      os.path.join(os.path.dirname(__file__), "assets")))
    os.makedirs(assets, exist_ok=True)

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
    async def assets_manifest(slot: str):
        return JSONResponse(asset_manifest(assets, slot))

    app.mount("/assets", StaticFiles(directory=assets), name="assets")
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
    parser.add_argument("--assets-dir", default=os.path.join(os.path.dirname(__file__), "assets"))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    logging.basicConfig(level=logging.DEBUG if options.debug else logging.INFO)
    uvicorn.run(create_app(options), host=options.host, port=options.port)
