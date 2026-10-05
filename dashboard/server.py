#!/usr/bin/env python3
import argparse
import asyncio
import collections
import copy
import contextlib
import ipaddress
import logging
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

REPO_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

import points
import live_params
import show_model
from show_engine import ShowEngine
from osc_bridge import FETCH_TIMEOUT_SECONDS, OSCBridge, source_for_peer
from monitor_transport import MonitorTransport
from editor_input import EditorInput
from python.paramgen import ParamGrammarError, parse_message
from ws_handlers import PATCH_NAME_RE as NAME_RE, WS_HANDLERS, WSHandlers

# The supervisor's stderr is the only place a launch failure explains itself:
# audition.py dies before send_ready() and the dashboard has already reported
# `running`. Keep a bounded tail per child and a bounded log of recent deaths,
# mirroring the Monitor's OSC transport-error treatment (61/2).
SUPERVISOR_LOG_LINES = 40
SUPERVISOR_ERROR_LIMIT = 20
SUPERVISOR_CAUSE_CHARS = 200


def drain_supervisor_stderr(stream, lines):
    """Read a supervisor's stderr to EOF, keeping only the tail.

    Runs on a reader thread for the child's whole life: an undrained PIPE
    blocks the child once the buffer fills, which would present as the editor
    hanging rather than crashing -- worse than the silence this replaces.
    """
    try:
        for raw in stream:
            text = raw.decode("utf-8", "replace").rstrip("\r\n")
            if text.strip():
                lines.append(text)
    except (OSError, ValueError):
        pass
    finally:
        try:
            stream.close()
        except OSError:
            pass


def supervisor_cause(lines):
    """The one line worth putting on a status: a traceback's last line."""
    for text in reversed(list(lines)):
        stripped = text.strip()
        if stripped:
            return stripped[:SUPERVISOR_CAUSE_CHARS]
    return ""
from state import (InstallationState, observed_active_patch, patch_badge,
                   reconcile_patch_switch_success)
from python import identity
from python import wifi_config
from python import io_catalog
from wifi_secrets import WifiSecrets
from python import asset_slots
from python import manifest as patch_manifest


log = logging.getLogger("bopos.dashboard")
OSC_ADDRESS_RE = re.compile(r"/(?!/)(?:[^\s#*,?\[\]{}]+/?)*[^\s/#*,?\[\]{}]")
PATCH_TEMPLATE = os.path.join(".templates", "bopos-template.pd")
PATCH_SWITCH_RECEIPT_SECONDS = 8.0
PATCH_SWITCH_RECONCILE_SECONDS = 2.0


def host_checkout_shorthand(repo_dir=REPO_DIR):
    """Return the dashboard host's checkout identity without failing startup."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_dir, "rev-parse", "--short=7", "HEAD"],
            capture_output=True, text=True, timeout=2, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{7,12}", value) else None


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
        if kind == "asset":
            names = asset_slots.installed_names(root)
        else:
            names = (name for name in os.listdir(root)
                     if NAME_RE.fullmatch(name) is not None
                     and not os.path.islink(os.path.join(root, name))
                     and os.path.isdir(os.path.join(root, name)))
        return [directory_info(root, name, kind) for name in sorted(names)]
    return {"assets": entries(assets_dir, "asset"),
            "patches": entries(patches_dir, "patch")}


class Dashboard(WSHandlers):
    def __init__(self, args):
        self.args = args
        self.state = InstallationState(args.data_dir, args.devices_file)
        self.wifi_secrets = WifiSecrets(self.state.data_dir)
        self.wifi_confirmations = {}
        self.clients = set()
        self.osc = OSCBridge(self.state, self.queue_broadcast, args.listen_port,
                             args.send_port, args.osc_target,
                             self.replay_live_params_for_seat,
                             stream_port=getattr(args, 'stream_port', 5551))
        self.osc.wifi_applied = self.wifi_applied
        self.monitor_transport = MonitorTransport(self)
        self.osc.tap = self.monitor_transport.tap
        self.tasks = set()
        self.sim_process = None
        self.supervisor_lock = asyncio.Lock()
        self.manifest_lock = asyncio.Lock()
        self.show_edit_lock = asyncio.Lock()
        self.show_undo = []
        self.supervisor_generation = 0
        self.supervisor_errors = []
        # One managed-audition subprocess owns the loopback command port.  Keep
        # sim_process as the compatibility handle used by the existing focused
        # verifies; supervisor.mode is the authority for what that child means.
        self.state.data["supervisor"] = {"mode": "off"}
        self.state.data["editor"] = {
            "active": False, "status": "off", "patch": None,
            "engine_alive": None, "generation": 0, "params": {},
            "declarations": [], "events": [], "points": {},
            "point_element": 0, "engine": None,
        }
        self.editor_input = EditorInput(self)
        self.fleet_operation = None
        self.fleet_retries = {}
        self.fleet_generation = 0
        self.performance_target = args.osc_target
        self.host_version = host_checkout_shorthand()
        self.assets_dir = os.path.realpath(getattr(args, "assets_dir", os.path.join(REPO_DIR, "assets")))
        self.patches_dir = os.path.realpath(getattr(args, "patches_dir", os.path.join(REPO_DIR, "patches")))
        # The editor's audition engine as a seat-shaped live automation target; see
        # editor_target(). `id` 0 is its OSC selector, `automation_key` keeps
        # its generator entries out of a real Seat 0's.
        self._editor_seat = {"id": 0, "automation_key": "editor",
                             "editor": True, "bound": None, "groups": [],
                             "params": {}}
        self.load_project_show()
        self.show_engine = ShowEngine(
            self.osc, self.broadcast,
            event_lead_ms=lambda: self.state.data.get("event_lead_ms", 500),
            resolve_targets=lambda targets: show_model.resolve_targets(
                targets, self.state.data.get("groups", {}))[0])
        self.show_engine.show = self.show
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
        try:
            if getattr(self, 'editor_input', None):
                self.editor_input.close()
        except Exception:
            logging.getLogger("bopos.dashboard").exception(
                "editor IO cleanup failed during dashboard shutdown")
        try:
            if getattr(self, 'monitor_transport', None):
                await self.monitor_transport.close()
        except Exception:
            logging.getLogger("bopos.dashboard").exception("Monitor cleanup failed")
        try:
            await self.stop_supervisor()
        except Exception:
            logging.getLogger("bopos.dashboard").exception(
                "supervisor cleanup failed during dashboard shutdown")
        try:
            for task in self.tasks:
                task.cancel()
            if self.tasks:
                await asyncio.gather(*tuple(self.tasks), return_exceptions=True)
        except Exception:
            logging.getLogger("bopos.dashboard").exception(
                "task cleanup failed during dashboard shutdown")
        try:
            self.osc.close()
        except Exception:
            logging.getLogger("bopos.dashboard").exception(
                "OSC cleanup failed during dashboard shutdown")
        try:
            await self.state.close()
        except Exception:
            logging.getLogger("bopos.dashboard").exception(
                "state cleanup failed during dashboard shutdown")

    def queue_broadcast(self, message_type, data=None):
        if self.monitor_transport.publish(message_type, data):
            return
        if not self.clients:
            return
        asyncio.create_task(self.broadcast(message_type, data))

    async def broadcast(self, message_type, data=None, *, priority=False):
        if not priority and self.monitor_transport.publish(message_type, data):
            return
        if message_type == "state":
            # A `state` broadcast has no caller-supplied payload and never has:
            # the enriched snapshot is the only thing any client can use, so it
            # is built here rather than trusted from 37 call sites.  Callers
            # pass nothing; anything passed is discarded.  Thread 50 exists
            # because the discarded argument used to be written out at most
            # call sites and read as if it decided what got sent.
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
                    # A transfer cannot survive the node it was running on.
                    self.osc.strand_device_fetches(uid)
                    await self.broadcast("device_offline", {"uid": uid})

    async def websocket(self, ws):
        await ws.accept()
        socket = ws
        ws = self.monitor_transport.attach(socket)
        self.clients.add(ws)
        await ws.send_json({"type": "state", "data": await self.public_state()})
        await ws.send_json({"type": "distribution", "data": await self.catalog()})
        # A browser reconnect is another full-state convergence edge. Replaying
        # the private listener is idempotent in the audition relay.
        self.osc.send_audition_listener()
        await ws.send_json({"type": "show", "data": self.show})
        await ws.send_json({"type": "show_warnings", "data": self.show_warnings()})
        await ws.send_json({"type": "show_playback", "data": self.show_engine.snapshot()})
        for device_uid, device in self.state.devices.items():
            if self.state.seat_for_uid(device_uid) and device.get("online"):
                self.osc.request(device_uid, "patches")
        try:
            while True:
                message = await socket.receive_json()
                await self.handle_ws(message, ws)
        except WebSocketDisconnect:
            pass
        finally:
            self.editor_input.release(ws)
            if self.editor_input.owner is ws:
                self.editor_input.clear()
                await self.broadcast("state")
            self.clients.discard(ws)
            self.wifi_confirmations.pop(ws, None)
            await ws.dispose()

    async def handle_ws(self, message, ws=None):
        kind, data = message.get("type"), message.get("data", {})
        policy = WS_HANDLERS.get(kind)
        if kind == "capture_selection" and ws in self.monitor_transport.clients:
            return await self._ws_capture_selection(kind, data, ws)
        error = self.ws_mode_error(policy, data)
        if error:
            return await self.ws_error(ws, error)
        if policy is None:
            return
        async with contextlib.AsyncExitStack() as locks:
            for required, lock_name in ((policy.manifest, "manifest_lock"),
                                       (policy.supervisor == "dispatch", "supervisor_lock")):
                if required:
                    await locks.enter_async_context(getattr(self, lock_name))
                    # An awaited lock may cross a mode transition. Recheck
                    # exactly where recursive dispatch used to recheck.
                    error = self.ws_mode_error(policy, data)
                    if error:
                        return await self.ws_error(ws, error)
            if self.ws_performance_locked(policy, data):
                return await self.ws_error(ws, "Performance")
            await getattr(self, policy.method)(kind, data, ws)

    def load_project_show(self):
        """Load the project's open show; a damaged file loads read-only.

        Same rule as project.json: the original is preserved, an invalid-file
        notice says so, and show writes are blocked until another show opens.
        An unmigrated show.json loads the same way, so it is never orphaned.
        """
        stale = getattr(self, "show_notice_path", None)
        if stale:
            self.state.data["notices"] = [notice for notice in self.state.data["notices"]
                                          if f'"{stale}"' not in notice]
        self.show, valid = show_model.load_show(self.state.show_path)
        damaged = self.state.legacy_show_path if self.state.show_unmigrated else (
            None if valid else self.state.show_path)
        # The file name is the show's name.
        self.show["name"] = self.state.data["current_show"]
        self.show_load_invalid = damaged is not None
        self.show_notice_path = damaged
        if damaged:
            self.state._invalid_file_notice(damaged)

    def show_playing(self):
        return bool(self.show_engine.playback)

    async def manage_show(self, kind, data, ws):
        """New, open, rename and delete a project's shows (66/10).

        Allowed in every mode, refused while a show is playing; opening one
        is the open-project sequence for the show alone.
        """
        name, failure = data.get("name"), {
            "open_show": "That show could not be opened.",
            "create_show": "The show could not be created.",
            "rename_show": "The show could not be renamed.",
            "delete_show": "The show could not be deleted."}[kind]
        async with self.show_edit_lock:
            if self.show_playing():
                await self.ws_error(ws, failure)
                return
            try:
                if kind == "open_show":
                    if name == self.state.data["current_show"]:
                        return
                    self.state.select_show(name)
                elif kind == "create_show":
                    source = data.get("source")
                    if source is not None and source not in self.state.list_shows():
                        raise ValueError("Show")
                    self.state.create_show(name, source)
                elif kind == "rename_show":
                    if name == self.state.data["current_show"]:
                        return
                    self.require_show_writable()
                    self.state.rename_show(name)
                    for doc in (self.show, *self.show_undo):
                        doc["name"] = name
                    await self.broadcast("show", self.show)
                    await self.broadcast("state")
                    return
                else:
                    self.state.delete_show(name)
                    await self.broadcast("state")
                    return
            except (OSError, TypeError, ValueError):
                await self.ws_error(ws, failure)
                return
            await self.show_engine.stop_all_steps()
            self.load_project_show()
            self.show_engine.show = self.show
            self.show_undo.clear()
            await self.broadcast("show", self.show)
            await self.broadcast("show_warnings", self.show_warnings())
            await self.broadcast("state")

    def project_unassign_set(self, candidate):
        bound = {seat.get("bound") for seat in candidate.seats.values() if seat.get("bound")}
        return sorted(uid for uid, device in self.state.devices.items()
                      if device.get("online") and not device.get("virtual") and uid not in bound)

    async def open_project(self, name):
        if self.supervisor_mode != "off":
            raise ValueError("Project")
        if name == self.state.project:
            return
        candidate = self.state.prepare_project(name)
        outside = self.project_unassign_set(candidate)
        async with self.show_edit_lock:
            await self.show_engine.stop_all_steps()
            self.state.select_project(candidate)
            self.supersede_fleet_operation()
            self.osc.automation.clear()
            self.state.data["automation"] = self.osc.automation
            self.wifi_confirmations.clear()
            self.load_project_show()
            self.show_engine.show = self.show
            self.show_undo.clear()
            for uid in outside:
                self.osc.uid_command(uid, "unassign")
            for seat in self.state.seats.values():
                self.assign_seat(seat)
                self.sync_seat_groups(seat)
                self.replay_live_params_for_seat(seat)
            self.osc.send_audition_listener()
            await self.broadcast("show", self.show)
            await self.broadcast("show_warnings", self.show_warnings())
            await self.broadcast("show_playback", self.show_engine.snapshot())
            await self.broadcast("state")

    def require_show_writable(self):
        # The show lives in the project folder: a project that failed to load
        # blocks its show's writes as it blocks its own, and so does a show
        # file that failed to load.
        self.state._require_valid_load()
        if self.show_load_invalid:
            raise OSError(
                f"Refusing to save a show that failed to load: {self.state.show_path}")

    def show_warnings(self):
        return show_model.show_target_warnings(
            self.show, self.state.data.get("groups", {}))

    async def apply_show_mutation(self, ws, mutate, *args):
        """Run one show_model edit op against the loaded show and persist it.

        `mutate` is any show_model function shaped (show, *args) -> (new_show,
        result, error); every WS edit message funnels through here so the
        persist-then-broadcast sequence exists exactly once (design note sec
        3: every mutation persists and re-broadcasts `show` full-state).
        """
        async with self.show_edit_lock:
            new_show, _result, error = mutate(self.show, *args)
            if error:
                await self.ws_error(ws, error)
                return
            if new_show == self.show:
                return
            try:
                self.require_show_writable()
                show_model.save_show(self.state.show_path, new_show)
            except OSError:
                await self.ws_error(ws, "The show could not be saved.")
                return
            self.show_undo.append(copy.deepcopy(self.show))
            del self.show_undo[:-100]
            self.show = new_show
            await self.show_engine.set_show(new_show)
            await self.broadcast("show", self.show)
            await self.broadcast("show_warnings", self.show_warnings())

    async def undo_show(self, ws):
        """Restore the last persisted Show edit for every connected client."""
        async with self.show_edit_lock:
            if not self.show_undo:
                return
            previous = self.show_undo.pop()
            try:
                self.require_show_writable()
                show_model.save_show(self.state.show_path, previous)
            except OSError:
                self.show_undo.append(previous)
                await self.ws_error(ws, "The show undo could not be saved.")
                return
            self.show = previous
            await self.show_engine.set_show(previous)
            await self.broadcast("show", self.show)
            await self.broadcast("show_warnings", self.show_warnings())

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

    def device_patch(self, uid, name):
        for patch in self.state.devices.get(uid, {}).get("patches") or ():
            if patch.get("name") == name:
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

    def live_control_manifest(self, patch_name=None):
        """Return the validated manifest for fleet or editor controls."""
        patch_name = patch_name or (self.state.data.get("fleet_patch") or {}).get("name")
        if not patch_name:
            return None
        manifest, _error = patch_manifest.load(os.path.join(self.patches_dir, patch_name))
        if manifest is None:
            return None
        return manifest

    def live_control_declarations(self, patch_name=None):
        """Validated full parameter schema for Seat-owned operator controls.

        `dashboard: true` is presentation metadata for the standalone
        facilitator view. The desktop Control and Device surfaces expose every
        declared parameter.
        """
        manifest = self.live_control_manifest(patch_name)
        if manifest is None:
            return []
        declarations = []
        for item in manifest.get("params", ()):
            projected = dict(item)
            projected["identity"] = patch_manifest.qualify_param(item)
            declarations.append(projected)
        return declarations

    def live_event_declarations(self, patch_name=None):
        """Declared event params for the staged patch.

        Events are carried beside the parameter schema rather than inside it:
        they are not `/p/*` values, so nothing that consumes `declarations`
        (replay and the Show message builder) should see them. The
        control panel fires them over the `<target>/e/*` wire (contract §3.2).
        """
        manifest = self.live_control_manifest(patch_name)
        if manifest is None:
            return []
        declarations = []
        for item in manifest.get("events", ()):
            projected = dict(item)
            projected["kind"] = "event"
            projected["identity"] = patch_manifest.qualify_param(item)
            declarations.append(projected)
        return declarations

    def replay_live_params_for_seat(self, seat):
        """Replay active automation, otherwise durable state, for one Seat."""
        patch_name = self.effective_patch_for_seat(seat)
        for declaration in self.live_control_declarations(patch_name):
            identity = declaration["identity"]
            args = live_params.replay_args(
                seat, declaration, self.osc.automation, time.time())
            if args is not None:
                # Replay is idempotent and must not replace sent_at: refreshing
                # that timestamp would resurrect an almost-complete fade.
                self.osc.send(f"/{int(seat['id'])}/p/{identity}", args)

    def editor_target(self):
        """The patch editor's audition engine, shaped as one concrete target.

        The editor drives OSC selector 0 on the private audition relay, but it
        is not Seat 0: it has no Device, no groups, and its durable mirror is
        the editor's own `params` map. Presenting it as a seat-shaped target
        keeps live parameter writes and automation on the shared target path.
        """
        editor = self.state.data["editor"]
        self._editor_seat["params"] = editor.setdefault("params", {})
        return self._editor_seat


    def effective_patch_for_seat(self, seat):
        """Return the editor patch or the staged fleet patch."""
        if seat.get("editor"):
            return self.state.data["editor"].get("patch")
        fleet = self.state.data.get("fleet_patch")
        if isinstance(fleet, dict) and isinstance(fleet.get("name"), str):
            return fleet["name"]
        return None


    def store_stopped_automation(self, seats, declaration, now=None):
        """Persist the dashboard's held-value estimate before sending Stop.

        Free LFO and sh/drift values are estimates: device-local phase is
        intentionally unknowable. Stop remains the wire command so divergent
        devices freeze in place instead of jumping to this dashboard estimate.
        """
        now = time.time() if now is None else float(now)
        identity = declaration["identity"]
        previous = [(target, dict(target["params"]) if "params" in target else None)
                    for target in [*seats, *self.state.devices.values()]]
        changed = False
        for seat in seats:
            entry = self.osc.automation.get(
                live_params.automation_key(seat), {}).get(identity)
            value = live_params.estimate_automation(
                identity, declaration, entry, now)
            if value is None:
                continue
            seat.setdefault("params", {})[identity] = value
            for device in self.state.devices.values():
                if (device.get("uid") == seat.get("bound")
                        or (device.get("virtual")
                            and str(device.get("seat_id")) == str(seat["id"]))):
                    device.setdefault("params", {})[identity] = value
            changed = True
        if changed:
            try:
                self.state.save()
            except (OSError, TypeError, ValueError):
                for target, params in previous:
                    if params is None:
                        target.pop("params", None)
                    else:
                        # Editor targets share this dict with editor state.
                        target["params"].clear()
                        target["params"].update(params)
                raise
        return changed


    def live_param_declaration(self, identity, patch_name=None):
        if not isinstance(identity, str):
            return None
        return next((item for item in self.live_control_declarations(patch_name)
                     if item["identity"] == identity), None)

    def live_scope_patch(self, scope, target_id):
        """Editor controls use the audition patch; other scopes use the fleet."""
        if scope == "editor":
            patch = self.state.data.get("editor", {}).get("patch")
            return patch if isinstance(patch, str) else None
        return None

    def live_param_target(self, scope, target_id):
        if scope == "editor":
            # Only meaningful while the editor owns the audio path; outside
            # Patch edit there is no engine on selector 0 to talk to.
            if self.supervisor_mode != "edit":
                return None, None
            return [self.editor_target()], 0
        if scope == "all":
            return list(self.state.seats.values()), "all"
        if scope == "seat":
            seat_id = self.state.clean_seat_id(target_id)
            seat = self.state.seats.get(str(seat_id))
            return ([seat], seat_id) if seat is not None else (None, None)
        if scope == "device":
            # A device-scoped write is a presentation scope over a seat
            # selector: OSC v1.5 targets content by seat.
            device = self.state.devices.get(target_id)
            if device is None or device.get("virtual"):
                return None, None
            seat = self.state.seat_for_uid(device.get("uid"))
            if seat is None:
                return None, None
            return [seat], int(seat["id"])
        if scope == "group":
            group_id = self.state.clean_group_id(target_id)
            if group_id is None or str(group_id) not in self.state.data.get("groups", {}):
                return None, None
            seats = self.state.seats_for_group(group_id)
            return (seats, f"g{group_id}") if seats else (None, None)
        return None, None

    def remote_action_selector(self, scope, target_id):
        """Resolve a Remote target card onto the selector-addressed /os plane."""
        if scope == "all":
            return "all"
        if scope == "seat":
            seat_id = self.state.clean_seat_id(target_id)
            return seat_id if str(seat_id) in self.state.seats else None
        if scope == "group":
            group_id = self.state.clean_group_id(target_id)
            return (f"g{group_id}"
                    if str(group_id) in self.state.data.get("groups", {})
                    else None)
        return None

    async def live_fleet_patch(self):
        staged = self.state.data.get("fleet_patch")
        if not staged:
            return None
        desired = dict(staged)
        item = await self.catalog_patch(desired["name"])
        if item is not None:
            desired["fingerprint"] = item["fingerprint"]
        return desired

    @property
    def wifi_changed(self):
        return self.wifi_secrets.pending

    def wifi_applied(self, uid, ssids):
        if not ssids:
            return
        pending = {key: set(names) for key, names in self.wifi_changed.items()}
        pending.setdefault(uid, set()).difference_update(ssids)
        try:
            self.wifi_secrets.save(self.wifi_secrets.values, pending)
        except OSError:
            # Retain the pending flags; a later send can safely retry the PSKs.
            pass

    def wifi_plans(self, config, secrets, changed):
        plans = []
        for uid, device in self.state.devices.items():
            if not device.get("online"):
                continue
            observed = wifi_config.redacted((device.get("report") or {}).get("wifi"))
            if not observed["managed"]:
                continue
            known = {row["ssid"] for row in observed["networks"] if row["secret"]} | set(observed["unmanaged"])
            rows = []
            for row in config["networks"]:
                name = row["ssid"]
                needed = name not in known or name in changed or name in self.wifi_changed.get(uid, ())
                secret = secrets.get(name) if needed else None
                if needed and secret is None:
                    raise ValueError("needs passphrase")
                rows.append(dict(row, psk=secret))
            plans.append((uid, {"country": config["country"], "networks": rows}))
        return plans

    async def send_wifi(self, config, ws, confirmed_count=None):
        secrets = {row["ssid"]: row["psk"] or self.wifi_secrets.values.get(row["ssid"])
                   for row in config["networks"]}
        secrets = {name: value for name, value in secrets.items() if value is not None}
        changed = {row["ssid"] for row in config["networks"] if row["psk"] is not None
                   and row["psk"] != self.wifi_secrets.values.get(row["ssid"])}
        try:
            plans = self.wifi_plans(config, secrets, changed)
        except ValueError:
            await self.ws_error(ws, "needs passphrase")
            return
        count = len({row["ssid"] for _, plan in plans for row in plan["networks"]
                     if row["psk"] is not None})
        if count and (confirmed_count is None or count > confirmed_count):
            if ws is not None:
                self.wifi_confirmations[ws] = (config, count)
                await ws.send_json({"type": "wifi_confirm", "data": {"passphrases": count}})
            return
        self.state._require_valid_load()
        previous_secrets, previous_list = dict(self.wifi_secrets.values), self.state.data["wifi"]
        previous_pending = {uid: set(names) for uid, names in self.wifi_changed.items()}
        pending = {uid: set(names) for uid, names in previous_pending.items()}
        for uid in set(self.state.devices) | set(self.state.device_registry):
            pending.setdefault(uid, set()).update(changed)
        self.wifi_secrets.save(secrets, pending)
        self.state.data["wifi"] = wifi_config.metadata(config)
        try:
            self.state.save()
        except OSError:
            self.state.data["wifi"] = previous_list
            self.wifi_secrets.save(previous_secrets, previous_pending)
            raise
        for uid, plan in plans:
            self.state.devices[uid]["wifi_apply"] = {"status": "pending", "phase": "applying"}
            self.osc.set_wifi_config(uid, plan)
        await self.broadcast("state")
        if ws is not None:
            await ws.send_json({"type": "wifi_saved", "data": {}})

    def wifi_sync(self, device):
        observed = wifi_config.redacted((device.get("report") or {}).get("wifi"))
        attempt = device.get("wifi_apply") or {}
        if attempt.get("status") == "pending":
            return "sending…"
        if attempt.get("status") == "err":
            return "error"
        if not observed["managed"]:
            return "no Wi-Fi"
        desired = self.state.data["wifi"]
        known = {row["ssid"] for row in observed["networks"] if row["secret"]} | set(observed["unmanaged"])
        if any(row["ssid"] not in known and row["ssid"] not in self.wifi_secrets.values
               for row in desired["networks"]):
            return "needs passphrase"
        if (self.wifi_changed.get(device["uid"]) or desired["country"] != observed["country"]
                or desired["networks"] != [{key: row[key] for key in ("ssid", "hidden", "enabled")}
                                           for row in observed["networks"]]):
            return "differs"
        return "in sync"

    async def public_device(self, device, desired=None):
        desired = desired if desired is not None else await self.live_fleet_patch()
        public = dict(device)
        # Alias is a projection of the durable host registry, never a runtime
        # device fact or node-provided identity.
        public["alias"] = (None if device.get("virtual")
                           else self.state.alias_for(device.get("uid")))
        if device.get("virtual"):
            public.update(device_enabled=True, enabled_observed=None,
                          output_enabled=True, enabled_status="unconfirmed")
        else:
            desired_enabled = self.state.device_enabled_for(device.get("uid"))
            observed = device.get("enabled_observed")
            pending_at = device.get("enabled_pending_at")
            if isinstance(observed, bool) and observed == desired_enabled:
                enabled_status = "current"
            elif pending_at is not None and time.time() - pending_at < 5.0:
                enabled_status = "pending"
            else:
                enabled_status = "unconfirmed"
            public.update(
                device_enabled=desired_enabled, enabled_observed=observed,
                output_enabled=device.get("output_enabled"),
                enabled_status=enabled_status)
        public["patch_badge"] = patch_badge(device, desired)
        public["wifi_sync"] = self.wifi_sync(device)
        return public

    async def public_state(self):
        desired = await self.live_fleet_patch()
        public = dict(self.state.public())
        public["performance"] = self.state.performance
        public["io_types"] = io_catalog.descriptions()
        public["wifi_secret_ssids"] = sorted(self.wifi_secrets.values)
        public["wifi_countries"] = sorted(wifi_config.COUNTRIES)
        # The durable record captures the identity staged by the operator, but
        # host edits make the live catalog identity the desired convergence
        # target.  Expose the same resolved identity used for row badges so UI
        # diagnostics never show an old digest beside an honestly stale row.
        public["fleet_patch"] = desired
        public["devices"] = {uid: await self.public_device(device, desired)
                             for uid, device in self.state.devices.items()}
        declarations = self.live_control_declarations()
        events = self.live_event_declarations()
        public["live_controls"] = {
            "patch": ((self.state.data.get("fleet_patch") or {}).get("name")
                      if declarations or events else None),
            "declarations": declarations,
            "events": events,
        }
        editor = dict(self.state.data["editor"])
        editor_device = self.state.devices.get("audition-0001")
        if self.supervisor_mode == "edit" and editor_device is not None:
            editor["engine_alive"] = int(editor_device.get("engine_alive") or 0)
            if editor["engine_alive"] == 0:
                editor["status"] = "engine closed"
        public["editor"] = editor
        editor["input"] = self.editor_input.snapshot()
        public["supervisor"] = {"mode": self.supervisor_mode}
        public["host_version"] = self.host_version
        return public

    @staticmethod
    def validate_event_command(data):
        selector = data.get("selector")
        event_identity = data.get("identity")
        elements = data.get("elements")
        if not isinstance(selector, str):
            return None, "Event selector must be a string."
        if not isinstance(event_identity, str):
            return None, "Event identity must be a string."
        identity_parts = event_identity.split("/")
        try:
            identity_bytes = event_identity.encode("ascii")
        except UnicodeEncodeError:
            identity_bytes = b""
        if (not 1 <= len(identity_parts) <= patch_manifest.MAX_PARAM_SEGMENTS
                or any(patch_manifest.PARAM_NAME.fullmatch(part) is None
                       for part in identity_parts)
                or len(identity_bytes) > patch_manifest.MAX_PARAM_IDENTITY_BYTES):
            return None, "Event identity does not match the /p/* segment grammar."
        if (not isinstance(elements, list)
                or len(elements) > patch_manifest.MAX_EVENT_ARITY
                or any(not isinstance(value, (int, float))
                       or isinstance(value, bool)
                       or not math.isfinite(value)
                       for value in elements)):
            return None, "Event elements must be a list of 0–3 finite numbers."
        return (selector, event_identity, [float(value) for value in elements]), None

    @staticmethod
    async def ws_error(ws, message):
        if ws is not None:
            await ws.send_json({"type": "error", "data": {"message": message}})

    @staticmethod
    def clean_monitor_message(data):
        if not isinstance(data, dict):
            return None, None, "OSC send payload is invalid."
        address = data.get("address")
        arguments = data.get("args")
        if (not isinstance(address, str) or len(address) > 255
                or OSC_ADDRESS_RE.fullmatch(address) is None):
            return None, None, "OSC address is invalid."
        if not isinstance(arguments, list) or len(arguments) > 64:
            return None, None, "OSC arguments are invalid."
        cleaned = []
        for argument in arguments:
            if not isinstance(argument, dict):
                return None, None, "OSC argument is invalid."
            kind, value = argument.get("type"), argument.get("value")
            if kind == "s":
                if not isinstance(value, str) or len(value) > 4096:
                    return None, None, "OSC string argument is invalid."
                cleaned.append(value)
                continue
            if kind == "i":
                if (isinstance(value, bool) or not isinstance(value, int)
                        or value < -2147483648 or value > 2147483647):
                    return None, None, "OSC integer argument is outside signed 32-bit range."
                cleaned.append(value)
                continue
            if kind == "f":
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    return None, None, "OSC float argument is invalid."
                number = float(value)
                if (not math.isfinite(number)
                        or number != float(format(number, ".6g"))):
                    return None, None, "OSC float needs at most 6 significant figures."
                cleaned.append(number)
                continue
            return None, None, "OSC argument type must be i, f, or s."
        return address, cleaned, None

    @staticmethod
    def clean_editor_value(declaration, value):
        if not isinstance(declaration, dict):
            return None
        kind = declaration.get("kind")
        if kind == "text":
            return value if isinstance(value, str) else None
        if kind not in {"float", "int", "toggle", "enum"} or isinstance(value, bool):
            return None
        try:
            cleaned = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(cleaned):
            return None
        if kind in {"int", "toggle", "enum"}:
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

        params, events = data.get("params"), data.get("events")
        if not isinstance(params, list) or not isinstance(events, list):
            await self.ws_error(ws, "Manifest params and events must be lists.")
            return
        candidate = dict(current)
        candidate["params"] = params
        candidate["events"] = events
        candidate["io_modules"] = data.get("io_modules", current.get("io_modules", []))
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
        editor["events"] = list(saved.get("events", ()))
        editor["io_modules"] = list(saved.get("io_modules", ()))
        if self.editor_input.source == "simulated":
            self.editor_input.reconcile()
        editor["params"] = {
            patch_manifest.qualify_param(declaration): previous_values.get(
                patch_manifest.qualify_param(declaration), declaration.get("default", ""))
            for declaration in declarations
        }
        response = {
            "patch": name,
            "params": declarations,
            "events": editor["events"],
            "io_modules": editor["io_modules"],
            "removed_params": removed,
            "added_params": added,
            "rename_candidates": rename_candidates,
            "pd_receive_warning": warning,
        }
        if ws is not None:
            await ws.send_json({"type": "manifest_saved", "data": response})
        await self.broadcast("distribution", await self.catalog())
        await self.broadcast("state")

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
                       "events": [], "caps": [], "slots": []}
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
        if self.state.add_project_patch(name):
            self.state.save_debounced()
            await self.broadcast("state")

    async def add_project_patch(self, data, ws):
        """Add Existing: list a valid catalog folder among the project's patches."""
        name = str(data.get("patch", "")).strip()
        if await self.catalog_patch(name) is None:
            await self.ws_error(ws, f"Cannot add {name!r}: no valid host patch.")
            return
        if self.state.add_project_patch(name):
            self.state.save_debounced()
            await self.broadcast("state")

    async def new_patch_version(self, data, ws):
        """New Version: copy the live patch folder under a new name.

        The fleet keeps running the Patch; the copy joins the project's
        patches and goes live only through Set Live.
        """
        live = (self.state.data.get("fleet_patch") or {}).get("name")
        source = self.patch_path(live or "")
        if source is None or not os.path.isdir(source):
            await self.ws_error(ws, "No fleet patch set")
            return
        name = str(data.get("name", "")).strip()
        target = self.patch_path(name)
        if target is None:
            await self.ws_error(ws, "Patch name: start with a letter or digit; then use letters, digits, dot, _ or -.")
            return
        if os.path.lexists(target):
            await self.ws_error(ws, f"Patch {name!r} already exists.")
            return
        try:
            await asyncio.to_thread(shutil.copytree, source, target, symlinks=True)
        except (OSError, shutil.Error) as error:
            if not isinstance(error, FileExistsError):
                await asyncio.to_thread(shutil.rmtree, target, True)
            await self.ws_error(ws, f"Could not create patch {name!r}: {error}")
            return
        self.state.add_project_patch(name)
        self.state.save_debounced()
        await self.broadcast("distribution", await self.catalog())
        await self.broadcast("state")

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
        await self.broadcast("state")
        await self.broadcast("distribution", await self.catalog())
        if generation != self.fleet_generation:
            return False
        if self.state.data["simulation"].get("active"):
            await self.restart_simulation()
            await self.broadcast("state")
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
        for device in self.state.devices.values():
            device["patch_switch"] = None
        return self.fleet_generation

    async def converge_fleet_patch(self, name, fingerprint, targets, base_urls,
                                   generation):
        """Converge bytes, then switch every ready online fleet target."""
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
            uri = f"{base_urls[uid]}/patches/{name}/.manifest.json"
            started = self.osc.fetch(uid, uri, slot, fingerprint)
            matched = (not started
                       and self.osc.fetch_matches(uid, slot, fingerprint))
            if started or matched:
                waiting.add(uid)
            else:
                await self.broadcast("error", {"message":
                    f"Patch transfer for {uid} could not start; another "
                    f"generation is already active for {slot}."})

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
        # A fleet deploy already owns convergence for the whole fleet. Retrying
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
        await self.broadcast("state")

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
        # Derive a device-reachable address ourselves whenever the operator
        # reached us at something that does not mean us from the node's side:
        # loopback, or an unspecified address (0.0.0.0 / ::, which run.sh binds
        # to and which a node resolves as *itself*). A hostname we cannot parse
        # is left alone — the venue may legitimately reach the dashboard by a
        # name the nodes also resolve.
        derive = request_hostname in (None, "localhost")
        if request_hostname not in (None, "localhost"):
            try:
                address = ipaddress.ip_address(request_hostname)
                derive = address.is_loopback or address.is_unspecified
            except ValueError:
                derive = False
        if not derive:
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
        try:
            if target_ip.version == 4:
                # Patch/asset HTTP transfers need the same direct-LAN source
                # selection as OSC. Ordinary macOS routing may otherwise pick
                # a tunnel advertising the installation subnet.
                local = source_for_peer(target)
            else:
                with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as route:
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
            self.osc.assign(uid, seat["id"], seat["name"], self.state.positions_for(seat["id"]))
            self.state.devices[uid]["params"] = dict(seat["params"])
            if self.state.devices[uid].get("online"):
                self.state.devices[uid]["revoking_assignment"] = False
        if self.state.data["simulation"].get("active"):
            for virtual_uid, device in self.state.devices.items():
                if (device.get("virtual")
                        and str(device.get("seat_id")) == str(seat["id"])):
                    self.osc.assign(virtual_uid, seat["id"], seat["name"], self.state.positions_for(seat["id"]))

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
        if mode != "edit":
            self.editor_input.clear()

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
        """Retarget and replay execution-owned state after private audition."""
        self.osc.set_target(self.performance_target)
        self.osc.send_master()
        self.osc.send_mute_all()

    async def record_supervisor_error(self, mode, returncode, lines):
        """Log an unexpected supervisor death and broadcast its tail.

        Only reached past `supervisor_exited`'s generation guard, so a
        deliberate stop -- which bumps the generation before terminating --
        never lands here.
        """
        cause = supervisor_cause(lines)
        payload = {
            "ts": time.time(),
            "mode": mode,
            "returncode": returncode,
            "cause": cause,
            "lines": list(lines),
        }
        self.supervisor_errors.append(payload)
        del self.supervisor_errors[:-SUPERVISOR_ERROR_LIMIT]
        logging.getLogger("bopos.dashboard").warning(
            "%s supervisor exited unexpectedly (rc=%s): %s",
            mode, returncode, cause or "no output captured")
        await self.broadcast("supervisor_error", payload)
        return cause

    async def supervisor_exited(self, process, mode, generation, lines=None,
                                reader=None):
        await asyncio.to_thread(process.wait)
        if reader is not None:
            # The child is gone, so EOF is imminent; bounded anyway rather than
            # letting a wedged reader hold the status line hostage.
            await asyncio.to_thread(reader.join, 2.0)
        if self.sim_process is not process or generation != self.supervisor_generation:
            return
        self.sim_process = None
        self.clear_audition_devices()
        cause = await self.record_supervisor_error(mode, process.returncode,
                                                   lines or ())
        status = f"stopped unexpectedly: {cause}" if cause else "stopped unexpectedly"
        if mode == "simulate":
            self.state.data["simulation"].update(active=False, status=status)
        else:
            self.state.data["editor"].update(active=False, status=status,
                                              engine_alive=None)
        self.set_supervisor_mode("off")
        self.restore_live_state()
        await self.broadcast("state")

    async def launch_supervisor(self, command, mode):
        self.supervisor_generation += 1
        generation = self.supervisor_generation
        try:
            process = subprocess.Popen(command, cwd=REPO_DIR,
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.PIPE)
        except OSError:
            self.clear_audition_devices()
            self.set_supervisor_mode("off")
            self.restore_live_state()
            return False
        lines = collections.deque(maxlen=SUPERVISOR_LOG_LINES)
        reader = threading.Thread(target=drain_supervisor_stderr,
                                  args=(process.stderr, lines),
                                  name=f"supervisor-stderr-{mode}", daemon=True)
        reader.start()
        self.sim_process = process
        self.spawn(self.supervisor_exited(process, mode, generation, lines, reader))
        return True

    async def stop_supervisor(self):
        if self.supervisor_mode == "edit":
            await self.stop_edit()
        elif self.supervisor_mode == "simulate":
            await self.stop_simulation()
        else:
            await self.terminate_supervisor_process()
            self.clear_audition_devices()

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
                      events=list(manifest.get("events", ())),
                      io_modules=list(manifest.get("io_modules", ())),
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
        self.editor_input.clear()
        await self.terminate_supervisor_process()
        self.clear_audition_devices()
        editor = self.state.data["editor"]
        editor.update(active=False, status="off", engine_alive=None, points={})
        self.set_supervisor_mode("off")
        self.restore_live_state()


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
            for position in dashboard.state.positions_for(seat["id"])[:2]:
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
    app.mount("/patches", DistributionStaticFiles(
        directory=patches), name="patches")
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
    parser.add_argument("--stream-port", type=int, default=5551)
    parser.add_argument("--send-port", type=int, default=6660)
    parser.add_argument("--osc-target", default="255.255.255.255")
    parser.add_argument("--data-dir", default=os.path.dirname(__file__),
                        help="Host data root containing projects/, devices.json and current-project")
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
