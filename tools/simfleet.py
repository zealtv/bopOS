#!/usr/bin/env python3
"""Simulated bopOS fleet speaking the currently deployed OSC wire protocol.

N fake devices heartbeat on 5550 and answer dashboard commands on 6660 exactly
as a real Pi does today (PD bopos.osc.pd + bopos.py together, seen from the
LAN). Use it to develop the dashboard, clock-sync, and scene work with zero
hardware:

    python3 tools/simfleet.py --devices 5
    python3 tools/simfleet.py --devices 5 --drop 0.05 --jitter-ms 30 --unresponsive 1
    python3 tools/simfleet.py --devices 4 --devices-file bopos.devices --target 127.0.0.1

Needs python-osc. The wire shapes are documented (and sourced) in the
dashboard-0-sim-fleet stitch's wire-protocol-today.md; when a stitch changes an
OSC message, extending this simulator is part of that stitch's deliverable —
message bytes live only in LegacyProtocol so the v1 contract can swap in there.
"""

import argparse
import csv
import datetime
import hashlib
import heapq
import itertools
import json
import os
import random
import re
import select
import socket
import sys
import time

from pythonosc import osc_message, osc_message_builder


REPO_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
PATCHES_DIR = os.path.join(REPO_DIR, "patches")
ASSETS_DIR = os.path.join(REPO_DIR, "assets")
DEVICE_ASSETS_DIR = "/home/pi/bopOS/assets"
DEFAULT_MANIFEST_PATH = os.path.join(REPO_DIR, "patches", "demo-pd", "bopos.patch.json")
HOSTNAME_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")

# the sim decomposes /pt with the same module the real helper uses, so the
# two can never drift (contract sec 4.1)
sys.path.append(os.path.join(REPO_DIR, "python"))
import identity  # noqa: E402
import manifest as patch_manifest  # noqa: E402
import pointfield  # noqa: E402
import groups as group_protocol  # noqa: E402
import paramgen  # noqa: E402
import audio_config  # noqa: E402
import log_config  # noqa: E402


def device_log_state(device):
    # Effective mirrors the real node: usb only if chosen *and* the stick is
    # present; otherwise internal (the visible fallback).
    effective = ("usb" if device.log_destination == "usb" and device.usb_present
                 else "internal")
    return {
        "destination": device.log_destination,
        "effective": effective,
        "usb_present": bool(device.usb_present),
    }


def load_manifest(path):
    """Return verbatim text and canonical declared parameter identities."""
    try:
        with open(path) as source:
            text = source.read()
        manifest_data = json.loads(text)
        if not isinstance(manifest_data, dict):
            return None, set()
        params = manifest_data.get("params", [])
        if not isinstance(params, list):
            return None, set()
        identities = [patch_manifest.qualify_param(param) for param in params]
        if len(identities) != len(set(identities)):
            return None, set()
        return text, set(identities)
    except (OSError, ValueError, TypeError, KeyError, UnicodeEncodeError):
        return None, set()


def manifest_declarations(text):
    if text is None:
        return {}
    try:
        params = json.loads(text).get("params", [])
        return {patch_manifest.qualify_param(item): item for item in params}
    except (ValueError, TypeError, AttributeError):
        return {}


DEFAULT_MANIFEST_TEXT, _DEFAULT_DECLARED_PARAMS = load_manifest(DEFAULT_MANIFEST_PATH)


def host_patch_fingerprint(name):
    # captured *now*, not at listing time: a device's copy is whatever the
    # host held when it converged, so a later host edit reads as stale.
    # Purely fake patches (git installs the sim never fetches) get a stable
    # fake identity so dashboards can still exercise match/mismatch.
    path = os.path.join(PATCHES_DIR, name)
    if os.path.isdir(path) and not os.path.islink(path):
        try:
            return identity.fingerprint(path)
        except OSError:
            pass
    return hashlib.sha256(name.encode()).hexdigest()


def host_asset_facts(root, name):
    """Snapshot the host slot using the catalog's canonical identity rules."""
    path = os.path.join(root, name)
    if os.path.isdir(path) and not os.path.islink(path):
        try:
            manifest = identity.directory_manifest(path)
            files = manifest["files"]
            return {
                "fingerprint": identity.manifest_fingerprint(manifest),
                "files": len(files),
                "bytes": sum(item["size"] for item in files),
            }
        except OSError:
            pass
    # Arbitrary file:/ test sources have no host catalog entry. Keep those
    # useful to the simulator with a valid, stable synthetic content identity.
    return {"fingerprint": hashlib.sha256(name.encode()).hexdigest(),
            "files": 0, "bytes": 0}


class ContractProtocol:
    """The OSC byte boundary for contract-v1 framework messages."""

    @staticmethod
    def decode(datagram):
        message = osc_message.OscMessage(datagram)
        return message.address, list(message.params)

    @staticmethod
    def matches(selector, device_id, memberships=()):
        return group_protocol.selector_matches(selector, device_id, memberships)

    @staticmethod
    def heartbeat(device):
        builder = osc_message_builder.OscMessageBuilder(address="/hb")
        builder.add_arg(device.mac, arg_type="s")
        builder.add_arg(int(device.device_id), arg_type="i")
        builder.add_arg(device.version, arg_type="s")
        builder.add_arg(device.engine_alive(), arg_type="i")
        if not device.wired:
            device.rssi = max(-80, min(-35, device.rssi + random.randint(-2, 2)))
            builder.add_arg(device.rssi, arg_type="i")
        return builder.build().dgram

    @staticmethod
    def pong(token, uid):
        builder = osc_message_builder.OscMessageBuilder(address="/os/pong")
        builder.add_arg(token)
        builder.add_arg(uid, arg_type="s")
        return builder.build().dgram


class Device:
    def __init__(self, mac, hostname, device_id, version, unresponsive=False,
                 wired=False, engine_dead=False, ephemeral=False):
        self.mac = mac
        self.hostname = hostname
        self.ephemeral = ephemeral
        self.device_id = device_id
        self.version = version
        self.unresponsive = unresponsive
        self.state = "booting"
        self.gain = 0.0
        self.gain2 = 0.0
        self.backing = 0.0
        self.params = {}
        self.active_patch = "demo-pd"
        self.patches = {
            "demo-pd": {"git": False, "manifest": DEFAULT_MANIFEST_TEXT is not None,
                        "fingerprint": host_patch_fingerprint("demo-pd")}
        }
        # Installed slots are snapshots: later host edits must not silently
        # alter a simulated node until another fetch converges that slot.
        self.asset_slots = {}
        # Launch-time engine context is a snapshot, not a live view of
        # inventory. It refreshes only on the simulated engine-start edges.
        self.engine_asset_paths = []
        self.reports = {}
        # Node-side log streams (contract sec 4.2 /log): stream name -> list of
        # (stamp, values) appended entries. In-memory parity for the real
        # node's append-only files; a verify harness inspects this.
        self.log_streams = {}
        # Log destination (contract sec 4.2 log-config): the bounded choice and
        # a simulated USB presence a verify harness can flip. Effective mirrors
        # the real node -- usb only if chosen *and* the stick is present.
        self.log_destination = "internal"
        self.usb_present = False
        self.last_hb = None
        self.last_command = "-"
        self.wired = wired
        self.engine_dead = engine_dead
        self.engine_restart_until = 0.0
        self.rssi = random.randint(-70, -45)
        self.device_enabled = True
        self.mute_all = False
        self.output_enabled = True
        self.audio_config = {
            "card": "Simulated", "mixer_control": "Master",
            "sample_rate": 44100, "period_size": 512, "nperiods": 2,
        }
        self.audio_active = dict(self.audio_config)
        self.audio_status = "active"
        self.audio_error = None
        self.ident_until = 0.0
        # clock-sync (contract sec 3.1): a fixed fake skew vs the leader's
        # clock, plus the offset the leader has pushed for event conversion
        self.sync_skew_ns = 0
        self.sync_offset_ns = 0
        self.sync_synced = False
        # /pt decomposition (contract sec 4.1): element positions from the
        # assignment (one [x, y] per element) and the held point field
        self.elements = []
        self.points = {}
        self.groups = ()

    def engine_alive(self):
        return int(not self.engine_dead
                   and self.state in ("booting", "running")
                   and time.monotonic() >= self.engine_restart_until)

    def capture_engine_context(self):
        self.engine_asset_paths = [
            os.path.join(DEVICE_ASSETS_DIR, name)
            for name in sorted(self.asset_slots)
        ]

    def wire_id(self):
        # list prepend 0 in bopos.osc.pd: reports carry id 0 until helper config lands
        return 0.0 if self.state == "booting" else self.device_id

    def match_id(self):
        # route-by-id's creation arg: an unconfigured device *listens* on -1, not 0
        return -1.0 if self.state == "booting" else self.device_id

    def display_state(self):
        return "unresponsive" if self.unresponsive and self.state != "off" else self.state

    def state_file(self, state_dir):
        return os.path.join(state_dir, self.mac.replace(":", "-") + ".json")

    def load_assignment(self, state_dir):
        # boot resolution, node-side: persisted assignment wins over the seed;
        # ephemeral devices sacrifice persistence and re-hello each boot
        if self.ephemeral:
            self.device_id = -1
            return
        try:
            with open(self.state_file(state_dir)) as source:
                assignment = json.load(source)
            self.device_id = int(assignment["id"])
            self.hostname = str(assignment.get("name", self.hostname))
            positions = assignment.get("positions") or []
            self.elements = [[float(positions[i]), float(positions[i + 1])]
                             for i in range(0, len(positions) - 1, 2)]
            self.groups = group_protocol.stored_group_ids(assignment.get("groups", []))
            legacy_enabled = "device_enabled" not in assignment
            if not legacy_enabled:
                self.device_enabled = bool(assignment["device_enabled"])
            else:
                self.device_enabled = not bool(
                    assignment.get("device_muted", False))
            self.output_enabled = bool(
                self.device_enabled and not self.mute_all)
            if legacy_enabled:
                flat_positions = [
                    coordinate for element in self.elements
                    for coordinate in element]
                self.save_assignment(state_dir, flat_positions)
        except (OSError, ValueError, KeyError, TypeError):
            pass

    def save_assignment(self, state_dir, positions, *, device_id=None, hostname=None,
                        memberships=None):
        if self.ephemeral or state_dir is None:
            return True
        saved_id = self.device_id if device_id is None else device_id
        saved_name = self.hostname if hostname is None else hostname
        saved_groups = self.groups if memberships is None else memberships
        try:
            os.makedirs(state_dir, exist_ok=True)
            tmp = self.state_file(state_dir) + ".tmp"
            with open(tmp, "w") as target:
                json.dump({"id": saved_id, "name": saved_name,
                           "positions": positions,
                           "groups": list(saved_groups),
                           "device_enabled": bool(self.device_enabled)}, target)
            os.replace(tmp, self.state_file(state_dir))
            return True
        except OSError as error:
            print(f"simfleet: could not persist assignment: {error}", file=sys.stderr)
            return False


class _DeviceSyncState:
    def __init__(self, device):
        self.device = device

    def offset(self):
        return self.device.sync_offset_ns

    def synced(self):
        return self.device.sync_synced


class SimFleet:
    def __init__(self, args, devices):
        self.args = args
        self.devices = devices
        self.protocol = ContractProtocol()
        self.manifest_text, self.declared_params = load_manifest(
            getattr(args, "manifest", None) or DEFAULT_MANIFEST_PATH)
        self.param_declarations = manifest_declarations(self.manifest_text)
        self.assets_dir = os.path.realpath(getattr(args, "assets_dir", ASSETS_DIR))
        self.events = []
        self.fetch_jobs = {}
        self.fetch_active = {}
        self.fetch_pending = {}
        self.sequence = itertools.count()
        self.running = True
        self.start_monotonic = time.monotonic()
        self.tty = sys.stdout.isatty()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("", args.cmd_port))
        self.sock.setblocking(False)
        self.target = (args.target, args.report_port)
        # each device gets a fixed clock skew in [-skew, +skew] so a correct
        # leader-pushed offset (contract sec 3.1) has something to cancel
        skew_ns = int(getattr(self.args, "sync_skew_ms", 0.0) * 1e6)
        for device in self.devices:
            device.sync_skew_ns = random.randint(-skew_ns, skew_ns) if skew_ns else 0
            if skew_ns:
                self.log(device, f"sync_skew={device.sync_skew_ns}ns")
            device.param_generator = paramgen.GeneratorEngine(
                lambda member, values, target=device: self.emit_param(target, member, values),
                _DeviceSyncState(device),
                lambda target=device: self.device_now_ns(target))

    def emit_param(self, device, member, values):
        if device.unresponsive or not device.engine_alive() or not values:
            return
        value = values[0]
        device.params[member] = value
        if member in ("gain", "gain2", "backing"):
            try:
                setattr(device, member, float(value))
            except (TypeError, ValueError):
                pass
        self.log(device, f"p/{member}={format_token(value)}")

    def schedule(self, delay, callback, *values):
        heapq.heappush(
            self.events,
            (time.monotonic() + max(0.0, delay), next(self.sequence), callback, values),
        )

    def log(self, device, message):
        if not self.tty:
            stamp = time.strftime("%H:%M:%S")
            print(f"{stamp} {device.hostname} id={device.device_id:g} {message}", flush=True)

    def set_state(self, device, state):
        if device.state != state:
            device.state = state
            self.log(device, f"state={device.display_state()}")

    def queue_datagram(self, datagram, heartbeat_device=None):
        if random.random() < self.args.drop:
            return
        delay = random.uniform(0.0, self.args.jitter_ms / 1000.0)
        self.schedule(delay, self.send_datagram, datagram, heartbeat_device)

    def send_datagram(self, datagram, heartbeat_device):
        try:
            self.sock.sendto(datagram, self.target)
            if heartbeat_device is not None:
                heartbeat_device.last_hb = time.monotonic()
        except OSError as error:
            print(f"simfleet: send failed: {error}", file=sys.stderr)

    def heartbeat(self, device, reschedule=True):
        if device.state in ("booting", "running"):
            self.queue_datagram(self.protocol.heartbeat(device), device)
        if reschedule:
            interval = 2.0 if device.device_id == -1 else self.args.hb_interval
            self.schedule(interval, self.heartbeat, device)

    def promote_running(self, device):
        if device.state == "booting":
            self.set_state(device, "running")

    def bump(self, device):
        device.version = f"{(int(device.version, 16) + 1) & 0xfffffff:07x}"

    def finish_boot(self, device, bump_version=False):
        if bump_version:
            self.bump(device)
        device.capture_engine_context()
        self.set_state(device, "booting")
        self.schedule(1.0, self.promote_running, device)
        self.schedule(0.0, self.heartbeat, device, False)

    def reboot_after_silence(self, device, bump_version=False):
        duration = self.args.boot_secs * random.uniform(0.7, 1.3)
        self.set_state(device, "rebooting")
        self.schedule(duration, self.finish_boot, device, bump_version)

    def send_rev(self, device, source, status=None, phase=None):
        # Optional status/phase make convergence failures attributable (v1.6).
        builder = osc_message_builder.OscMessageBuilder(address="/os/rev")
        builder.add_arg(str(device.version), arg_type="s")
        builder.add_arg("ephemeral" if device.ephemeral else "persistent", arg_type="s")
        builder.add_arg(device.mac, arg_type="s")
        if status is not None:
            builder.add_arg(str(status), arg_type="s")
            builder.add_arg(str(phase or "unknown"), arg_type="s")
        try:
            self.sock.sendto(builder.build().dgram, (source[0], self.args.report_port))
        except OSError as error:
            print(f"simfleet: rev reply failed: {error}", file=sys.stderr)

    def send_patch_list(self, device, source):
        listing = []
        for name, facts in sorted(device.patches.items()):
            entry = {
                "name": name,
                "active": name == device.active_patch,
                "git": facts["git"],
                "manifest": facts["manifest"],
            }
            if facts.get("fingerprint"):
                entry["fingerprint"] = facts["fingerprint"]
            listing.append(entry)
        builder = osc_message_builder.OscMessageBuilder(address="/os/patches")
        builder.add_arg(json.dumps(listing, separators=(",", ":")), arg_type="s")
        self.sock.sendto(builder.build().dgram, (source[0], self.args.report_port))

    def send_asset_list(self, device, source):
        listing = [{"name": name, **facts}
                   for name, facts in sorted(device.asset_slots.items())]
        builder = osc_message_builder.OscMessageBuilder(address="/os/assets")
        builder.add_arg(json.dumps(listing, separators=(",", ":")), arg_type="s")
        self.sock.sendto(builder.build().dgram, (source[0], self.args.report_port))

    def send_report(self, device, source):
        audio = {
            "configured": dict(device.audio_config),
            "active": dict(device.audio_active),
            "cards": [{
                "id": "Simulated", "index": 0,
                "label": "Simulated stereo output",
                "mixer_controls": ["Master"],
            }],
            "status": device.audio_status,
            "error": device.audio_error,
        }
        report = {
            "uid": device.mac,
            "hostname": device.hostname,
            "engine": "pd",
            "has_i2c": False,
            "has_wifi": not device.wired,
            "audio_channels": 2,
            "screen": False,
            "patch": device.active_patch,
            "uptime": int(time.monotonic() - self.start_monotonic),
            "git_rev": device.version,
            "update_model": "ephemeral" if device.ephemeral else "persistent",
            "contract_version": "1.16",
            "groups": list(device.groups),
            "device_enabled": bool(device.device_enabled),
            "mute_all": bool(device.mute_all),
            "output_enabled": bool(device.output_enabled),
            "audio": audio,
            "log": device_log_state(device),
        }
        builder = osc_message_builder.OscMessageBuilder(address="/os/report")
        builder.add_arg(json.dumps(report), arg_type="s")
        self.sock.sendto(builder.build().dgram, (source[0], self.args.report_port))

    def uid_admin(self, device, member, args, source):
        allowed = {"identify", "report", "reboot", "shutdown", "restart-engine",
                   "updatebopos", "unassign"}
        if member == "enabled" and len(args) == 1:
            try:
                value = int(args[0])
            except (TypeError, ValueError):
                return
            if value not in (0, 1):
                return
            previous = device.device_enabled
            device.device_enabled = bool(value)
            positions = [coordinate for element in device.elements for coordinate in element]
            if not device.save_assignment(self.args.state_dir, positions):
                device.device_enabled = previous
                return
            device.output_enabled = bool(
                device.device_enabled and not device.mute_all)
            builder = osc_message_builder.OscMessageBuilder(address="/os/enabled")
            builder.add_arg(device.mac, arg_type="s")
            builder.add_arg(value, arg_type="i")
            builder.add_arg(int(device.output_enabled), arg_type="i")
            self.sock.sendto(builder.build().dgram,
                             (source[0], self.args.report_port))
            self.log(
                device,
                f"device_enabled={value} output={int(device.output_enabled)}")
            return
        if member == "hostname" and len(args) == 1:
            hostname = str(args[0])
            if HOSTNAME_RE.fullmatch(hostname) is None:
                return
            positions = [coordinate for element in device.elements for coordinate in element]
            status = "ok" if device.save_assignment(
                self.args.state_dir, positions, hostname=hostname) else "err"
            if status == "ok":
                device.hostname = hostname
            builder = osc_message_builder.OscMessageBuilder(address="/os/hostname")
            builder.add_arg(device.mac, arg_type="s")
            builder.add_arg(hostname, arg_type="s")
            builder.add_arg(status, arg_type="s")
            self.sock.sendto(builder.build().dgram,
                             (source[0], self.args.report_port))
            if status == "ok":
                self.heartbeat(device, reschedule=False)
            self.log(device, f"hostname={hostname} {status}")
            return
        if member == "audio-config" and len(args) == 1:
            cards = [{
                "id": "Simulated", "index": 0,
                "label": "Simulated stereo output",
                "mixer_controls": ["Master"],
            }]
            try:
                candidate = audio_config.validate(json.loads(str(args[0])), cards)
                device.audio_config = candidate
                device.audio_active = dict(candidate)
                device.audio_status = "active"
                device.audio_error = None
                status, phase = "ok", "applied"
            except (ValueError, TypeError) as error:
                device.audio_status = "error"
                device.audio_error = str(error)
                status, phase = "err", "invalid"
            payload = {
                "configured": dict(device.audio_config),
                "active": dict(device.audio_active),
                "cards": cards,
                "status": device.audio_status,
                "error": device.audio_error,
            }
            builder = osc_message_builder.OscMessageBuilder(
                address="/os/audio-config")
            builder.add_arg(device.mac, arg_type="s")
            builder.add_arg(status, arg_type="s")
            builder.add_arg(phase, arg_type="s")
            builder.add_arg(json.dumps(payload, separators=(",", ":")), arg_type="s")
            self.sock.sendto(builder.build().dgram,
                             (source[0], self.args.report_port))
            return
        if member == "log-config" and len(args) == 1:
            try:
                candidate = log_config.validate(json.loads(str(args[0])))
                device.log_destination = candidate["destination"]
                status = "ok"
            except (ValueError, TypeError):
                status = "err"
            builder = osc_message_builder.OscMessageBuilder(
                address="/os/log-config")
            builder.add_arg(device.mac, arg_type="s")
            builder.add_arg(status, arg_type="s")
            builder.add_arg(
                json.dumps(device_log_state(device), separators=(",", ":")),
                arg_type="s")
            self.sock.sendto(builder.build().dgram,
                             (source[0], self.args.report_port))
            self.log(device, f"log-config {device.log_destination} {status}")
            return
        if member not in allowed or args:
            return
        if member == "identify":
            device.ident_until = time.monotonic() + 3.0
            self.log(device, "identify")
        elif member == "report":
            self.send_report(device, source)
        elif member == "unassign":
            if not device.save_assignment(self.args.state_dir, [], device_id=-1,
                                          memberships=()):
                return
            device.groups = ()
            device.device_id = -1
            device.elements = []
            self.log(device, "unassigned")
            self.heartbeat(device, reschedule=False)
        else:
            self.admin_verb(device, member, [], source)

    def send_fetch_state(self, source, slot, state):
        builder = osc_message_builder.OscMessageBuilder(address="/os/fetch-progress")
        builder.add_arg(slot, arg_type="s")
        builder.add_arg(state, arg_type="s")
        self.sock.sendto(builder.build().dgram, (source[0], self.args.report_port))

    def begin_fetch(self, key):
        job = self.fetch_jobs.get(key)
        if job is None:
            return
        job["phase"] = "fetching"
        if job["active"]:
            job["device"].engine_restart_until = float("inf")
        for source in job["requesters"]:
            self.send_fetch_state(source, job["slot"], "fetching")
        self.schedule(getattr(self.args, "fetch_seconds", 0.9), self.finish_fetch, key)

    def finish_fetch(self, key):
        job = self.fetch_jobs.pop(key, None)
        if job is None:
            return
        device, slot = job["device"], job["slot"]
        if job["active"]:
            device.capture_engine_context()
            device.engine_restart_until = 0.0
        ok = job["ok"]
        if ok:
            if slot.startswith("patch:"):
                name = slot.split(":", 1)[1]
                # fetch converged the copy to the host's current content
                device.patches[name] = {"git": False, "manifest": True,
                                        "fingerprint": host_patch_fingerprint(name)}
            else:
                device.asset_slots[slot] = host_asset_facts(self.assets_dir, slot)
        for source in job["requesters"]:
            builder = osc_message_builder.OscMessageBuilder(address="/os/fetched")
            builder.add_arg(slot, arg_type="s")
            builder.add_arg("ok" if ok else "err", arg_type="s")
            self.sock.sendto(builder.build().dgram, (source[0], self.args.report_port))
        mac = device.mac
        if self.fetch_active.get(mac) == key:
            self.fetch_active.pop(mac, None)
        pending = self.fetch_pending.get(mac, [])
        if pending:
            next_key = pending.pop(0)
            self.fetch_active[mac] = next_key
            self.schedule(0.1, self.begin_fetch, next_key)
        else:
            self.fetch_pending.pop(mac, None)

    def queue_fetch(self, device, source, uri, slot):
        key = (device.mac, uri, slot)
        existing = self.fetch_jobs.get(key)
        if existing is not None:
            existing["requesters"].append(source)
            self.send_fetch_state(source, slot, existing["phase"])
            return
        job = {
            "device": device,
            "requesters": [source],
            "slot": slot,
            "phase": "queued",
            "active": slot == "patch:" + device.active_patch,
            "ok": True,
        }
        self.fetch_jobs[key] = job
        self.send_fetch_state(source, slot, "queued")
        if device.mac not in self.fetch_active:
            self.fetch_active[device.mac] = key
            self.schedule(0.1, self.begin_fetch, key)
        else:
            self.fetch_pending.setdefault(device.mac, []).append(key)

    def finish_patch_switch(self, device, source):
        device.capture_engine_context()
        device.engine_restart_until = 0.0
        self.send_rev(device, source, "ok", "switched")

    def finish_engine_restart(self, device):
        device.capture_engine_context()
        device.engine_restart_until = 0.0

    def admin_verb(self, device, member, args, source):
        # bopos.py owns these, so a dead engine still answers
        self.log(device, f"os/{member} {' '.join(format_token(item) for item in args)}".rstrip())
        provisioning = member in ("updatebopos", "checkout", "patch",
                                  "addpatch", "pullpatch", "droppatch",
                                  "dropassets")
        if provisioning and device.ephemeral:
            # ephemeral: honest no-op, receipt still sent (contract sec 7)
            self.send_rev(device, source)
            return
        if member == "reboot":
            self.send_rev(device, source)  # lifecycle replies before executing
            self.schedule(0.5, self.reboot_after_silence, device)
        elif member == "shutdown":
            self.send_rev(device, source)
            self.schedule(0.5, self.set_state, device, "off")
        elif member == "restart-engine":
            self.send_rev(device, source)
            device.engine_restart_until = float("inf")
            self.schedule(3.0, self.finish_engine_restart, device)
        elif member == "updatebopos" or (member == "checkout" and args):
            # the pull lands (sha bumps), the receipt goes out, then the reboot
            self.set_state(device, "updating")
            self.bump(device)
            self.schedule(2.0, self.send_rev, device, source, "ok", "converged")
            self.schedule(5.0, self.reboot_after_silence, device, False)
        elif member == "patch":
            if not args:
                self.send_rev(device, source, "err", "invalid-name")
                return
            name = str(args[0])
            if name not in device.patches or not device.patches[name]["manifest"]:
                self.send_rev(device, source, "err", "not-found")
                return
            device.active_patch = name
            device.engine_restart_until = float("inf")
            self.schedule(2.0, self.finish_patch_switch, device, source)
        elif member == "addpatch":
            if len(args) < 2:
                self.send_rev(device, source, "err", "invalid-args")
                return
            device.patches[str(args[1])] = {"git": True, "manifest": True,
                                            "fingerprint": host_patch_fingerprint(str(args[1]))}
            self.schedule(1.0, self.send_rev, device, source, "ok", "cloned")
        elif member == "pullpatch":
            self.schedule(1.0, self.send_rev, device, source, "ok", "pulled")
        elif member == "droppatch":
            if not args:
                self.send_rev(device, source, "err", "invalid-name")
                return
            name = str(args[0])
            if name == device.active_patch:
                self.send_rev(device, source, "err", "active-patch")
                return
            device.patches.pop(name, None)
            self.send_rev(device, source, "ok", "dropped")
        elif member == "dropassets":
            if not args or not identity.valid_asset_slot(str(args[0])):
                self.send_rev(device, source, "err", "invalid-name")
                return
            device.asset_slots.pop(str(args[0]), None)
            self.send_rev(device, source, "ok", "dropped")
        else:
            # malformed args change nothing; the receipt is still the honest state
            self.send_rev(device, source)

    def device_now_ns(self, device, jitter=False):
        # the device's own monotonic clock = leader's clock + its fixed skew;
        # a pong may add per-reply measurement noise
        value = time.monotonic_ns() + device.sync_skew_ns
        if jitter and self.args.sync_jitter_ms > 0:
            span = int(self.args.sync_jitter_ms * 1e6)
            value += random.randint(-span, span)
        return value

    def handle_ping(self, args, source):
        # bopos.py answers /sync/ping unicast, echoing seq+leaderTime so the
        # leader stays stateless (contract sec 3.1)
        if len(args) < 2:
            return
        try:
            seq = int(args[0])
        except (TypeError, ValueError):
            return
        leader_time = str(args[1])
        for device in self.devices:
            if device.unresponsive or device.state not in ("booting", "running"):
                continue
            if random.random() < self.args.drop:
                continue
            builder = osc_message_builder.OscMessageBuilder(address="/sync/pong")
            builder.add_arg(seq, arg_type="i")
            builder.add_arg(leader_time, arg_type="s")
            builder.add_arg(device.mac, arg_type="s")
            builder.add_arg(str(self.device_now_ns(device, jitter=True)), arg_type="s")
            try:
                self.sock.sendto(builder.build().dgram,
                                 (source[0], self.args.report_port))
            except OSError as error:
                print(f"simfleet: pong failed: {error}", file=sys.stderr)

    def handle_offset(self, selector, args):
        # /<id>/sync/offset: absolute best-estimate offset, idempotent. A real
        # node slews toward it; the sim stores the target directly.
        if not args:
            return
        try:
            offset = int(str(args[0]))
        except (TypeError, ValueError):
            return
        for device in self.devices:
            if device.unresponsive or device.state not in ("booting", "running"):
                continue
            if not self.protocol.matches(selector, device.device_id, device.groups):
                continue
            device.sync_offset_ns = offset
            device.sync_synced = True
            self.log(device, f"sync offset={offset}ns")

    def apply_points(self, device, parts, args):
        # node-side decomposition (contract sec 4.1) via the shared helper
        # module: proximity per point per element, "delivered" by logging
        # `pt <id> el<n> v=<value>` (the fake device has no engine). The log
        # is the verify's test surface for node-computed values.
        parsed = pointfield.parse_wire(parts, args)
        if parsed is None:
            return
        kind, payload = parsed
        if kind == "frame":
            removed = set(device.points) - set(payload)
            device.points = payload
            changed = payload
        elif kind == "set":
            point_id, point = payload
            device.points[point_id] = point
            removed = set()
            changed = {point_id: point}
        else:  # clear
            removed = {payload} if payload in device.points else set()
            device.points.pop(payload, None)
            changed = {}
        if not device.elements:
            return
        entries = pointfield.decompose(changed, device.elements)
        for point_id in sorted(removed):
            for index in range(len(device.elements)):
                entries.append((point_id, index, 0.0))
        for point_id, element, value in entries:
            self.log(device, f"pt {point_id} el{element} v={value:.6f}")

    def handle_event(self, parts, args):
        identity_parts = parts[2:]
        identity = "/".join(identity_parts)
        if (len(identity_parts) > patch_manifest.MAX_PARAM_SEGMENTS
                or any(patch_manifest.PARAM_NAME.fullmatch(part) is None
                       for part in identity_parts)
                or len(identity.encode("ascii")) > patch_manifest.MAX_PARAM_IDENTITY_BYTES
                or not 1 <= len(args) <= patch_manifest.MAX_EVENT_ARITY + 1
                or not isinstance(args[0], str)
                or any(not isinstance(value, float) for value in args[1:])):
            return
        try:
            elements = [float(value) for value in args[1:]]
            shared = int(args[0])
        except (TypeError, ValueError):
            return
        selector = parts[0]
        for device in self.devices:
            if (device.unresponsive or device.state not in ("booting", "running")
                    or random.random() < self.args.drop
                    or not self.protocol.matches(
                        selector, device.device_id, device.groups)):
                continue
            if args[0] == "0":
                self.fire_event(device, identity, elements, 0, False)
                continue
            deadline_dev = shared + device.sync_offset_ns
            delay = (
                deadline_dev - device.sync_skew_ns - time.monotonic_ns()) / 1e9
            self.schedule(max(0.0, delay), self.fire_event, device, identity,
                          elements, deadline_dev, delay < 0)

    def fire_event(self, device, identity, elements, deadline_dev, late):
        values = " ".join(format_token(value) for value in elements)
        suffix = f" elements={values}" if values else ""
        self.log(device, f"event {identity} fired dev_deadline={deadline_dev} "
                         f"fire_mono={time.monotonic_ns()}{suffix}"
                         + (" LATE" if late else ""))

    ADMIN_ACTIONS = ("update-patch", "update-bopos", "shutdown", "reboot")

    def admin_request(self, device, action):
        # a real node's engine sends /admin <action> to bopos.py on localhost
        # 7770 (contract sec 4.2, v1.7); that channel is per-node and never
        # touches the LAN wire this simulator answers on 5550/6660. N
        # simulated devices share one process, so unlike N real Pis they
        # cannot each bind a private localhost 7770 -- there is no socket
        # for this method to listen on. It exists as the direct call a
        # verify harness drives to exercise the same log/record-only,
        # never-execute contract bopos.py's admin_callback implements
        # (never actually reboot/shutdown/update the sim host; unknown
        # actions are logged and otherwise ignored).
        if action not in self.ADMIN_ACTIONS:
            self.log(device, f"admin unknown-action={action}")
            return
        self.log(device, f"admin {action}")

    def log_request(self, device, stream, values):
        # a real node's engine sends /log <stream> <values...> to bopos.py on
        # localhost 7770 (contract sec 4.2); like /admin, that per-node
        # channel never touches the LAN wire this simulator answers on, and N
        # simulated devices share one process with no private 7770 to bind.
        # This is the direct call a verify harness drives to exercise the same
        # stamp/append/validate contract nodelog.append implements. Invalid
        # stream names are dropped with a logged warning, never fatal; the
        # node stamps at receipt.
        stream = str(stream)
        if re.fullmatch(r"[A-Za-z0-9_-]+", stream) is None:
            self.log(device, f"log invalid-stream={stream!r}")
            return
        stamp = datetime.datetime.now().astimezone().isoformat(
            timespec="milliseconds")
        payload = " ".join(format_token(value) for value in values)
        device.log_streams.setdefault(stream, []).append((stamp, list(values)))
        self.log(device, f"log {stream} {payload}".rstrip())

    def receive(self):
        while True:
            try:
                datagram, source = self.sock.recvfrom(65535)
            except BlockingIOError:
                return
            self.receive_contract(datagram, source)

    def receive_contract(self, datagram, source):
        try:
            address, args = self.protocol.decode(datagram)
        except Exception:
            return
        parts = [part for part in address.split("/") if part]
        # Clock-sync ping omits the selector; events are targetable and offsets
        # are per-device.
        if parts == ["sync", "ping"]:
            self.handle_ping(args, source)
            return
        if len(parts) >= 3 and parts[1] == "e":
            self.handle_event(parts, args)
            return
        if len(parts) == 3 and parts[1] == "sync" and parts[2] == "offset":
            self.handle_offset(parts[0], args)
            return
        if parts and parts[0] == "pt":
            # /pt plane: selector-less broadcast geometry; each device's own
            # radio may drop it independently (silence = hold covers the gap
            # until the next frame)
            for device in self.devices:
                if device.unresponsive or device.state not in ("booting", "running"):
                    continue
                if random.random() < self.args.drop:
                    continue
                self.apply_points(device, parts, args)
            return
        if parts == ["all", "os", "to"]:
            if len(args) < 2:
                return
            uid, member, member_args = str(args[0]), str(args[1]), list(args[2:])
            for device in self.devices:
                if (device.unresponsive or device.state not in ("booting", "running")
                        or device.mac != uid or random.random() < self.args.drop):
                    continue
                self.uid_admin(device, member, member_args, source)
            return
        if parts == ["all", "os", "groups"]:
            if not args or not isinstance(args[0], str):
                return
            memberships = group_protocol.group_ids(args[1:])
            if memberships is None:
                return
            for device in self.devices:
                if (device.unresponsive or device.state not in ("booting", "running")
                        or device.mac != args[0] or random.random() < self.args.drop):
                    continue
                positions = [coordinate for element in device.elements for coordinate in element]
                if not device.save_assignment(self.args.state_dir, positions,
                                              memberships=memberships):
                    continue
                device.groups = memberships
                builder = osc_message_builder.OscMessageBuilder(address="/os/groups")
                builder.add_arg(device.mac, arg_type="s")
                for group_id in memberships:
                    builder.add_arg(group_id, arg_type="i")
                self.sock.sendto(builder.build().dgram,
                                 (source[0], self.args.report_port))
            return
        if len(parts) < 3 or parts[1] not in ("os", "p"):
            return
        selector, plane = parts[:2]
        if plane == "os" and len(parts) != 3:
            return
        member = "/".join(parts[2:])
        for device in self.devices:
            # bopos.py answers these, so the box must be up (booting counts:
            # helper starts before the engine) and its radio listening
            if device.unresponsive or device.state not in ("booting", "running"):
                continue
            if (random.random() < self.args.drop
                    or not self.protocol.matches(selector, device.device_id, device.groups)):
                continue
            if plane == "p":
                # the patch plane goes straight to PD — a dead engine applies nothing
                if not args or not device.engine_alive():
                    continue
                if member not in self.declared_params and member not in ("gain", "gain2", "backing"):
                    self.log(device, f"p/{member} undeclared, dropped")
                    continue
                declaration = getattr(self, "param_declarations", {}).get(member)
                param_type = patch_manifest.param_wire_type(declaration)
                if param_type in ("f", "i"):
                    try:
                        spec = paramgen.parse_message(args, param_type)
                    except paramgen.ParamGrammarError as error:
                        self.log(device, f"p/{member} grammar error: {error}")
                        continue
                    device.param_generator.apply(member, spec, declaration)
                else:
                    self.emit_param(device, member, args)
                continue
            if member == "ping" and args:
                try:
                    self.sock.sendto(self.protocol.pong(args[0], device.mac),
                                     (source[0], self.args.report_port))
                except OSError as error:
                    print(f"simfleet: pong failed: {error}", file=sys.stderr)
            elif member == "assign" and len(args) >= 3:
                if selector != "all":
                    continue
                if str(args[0]) != device.mac:
                    continue
                try:
                    new_id = int(args[1])
                except (TypeError, ValueError):
                    continue
                if (isinstance(args[1], bool) or not isinstance(args[1], (int, float))
                        or float(args[1]) != new_id
                        or not 0 <= new_id <= group_protocol.INT32_MAX):
                    continue
                hostname = str(args[2])
                # true-N element positions: one x y pair per element, pair
                # order = element index (contract sec 5)
                if (len(args[3:]) % 2
                        or any(isinstance(value, bool)
                               or not isinstance(value, (int, float))
                               for value in args[3:])):
                    continue
                positions = [float(value) for value in args[3:]]
                memberships = device.groups if new_id == device.device_id else ()
                if not device.save_assignment(self.args.state_dir, positions,
                                              device_id=new_id, hostname=hostname,
                                              memberships=memberships):
                    continue
                device.groups = memberships
                device.device_id = new_id
                device.hostname = hostname
                device.elements = [[positions[i], positions[i + 1]]
                                   for i in range(0, len(positions) - 1, 2)]
                # Preview relay tests need the ordered element state but the
                # protocol simulator must not pretend to render audio.
                preview_positions = json.dumps(device.elements, separators=(",", ":"))
                self.log(device, f"assigned id={device.device_id:g} name={device.hostname} "
                         f"positions={preview_positions}")
                # the ack is an immediate heartbeat at the new id; the running
                # schedule picks up the new cadence on its own
                self.heartbeat(device, reschedule=False)
            elif member == "identify" and (not args or str(args[0]) == device.mac):
                device.ident_until = time.monotonic() + 3.0
                self.log(device, "identify")
            elif member == "mute" and args:
                try:
                    value = int(args[0])
                except (TypeError, ValueError):
                    continue
                if value in (0, 1):
                    device.mute_all = bool(value)
                    device.output_enabled = bool(
                        device.device_enabled and not device.mute_all)
                    self.log(
                        device,
                        f"mute_all={value} output={int(device.output_enabled)}")
            elif member == "master" and args:
                # provided term (contract sec 4.1): a real node's OS layer
                # routes this to the engine's named receive; the fake device
                # has no engine, so delivery is just logged
                try:
                    self.log(device, f"os/master {float(args[0]):g}")
                except (TypeError, ValueError):
                    pass
            elif member == "params":
                builder = osc_message_builder.OscMessageBuilder(address="/os/params")
                if self.manifest_text is not None:
                    builder.add_arg(self.manifest_text, arg_type="s")
                self.sock.sendto(builder.build().dgram, (source[0], self.args.report_port))
            elif member == "patches":
                self.send_patch_list(device, source)
            elif member == "assets":
                self.send_asset_list(device, source)
            elif member == "fetch":
                uri = str(args[0]) if args else ""
                slot = str(args[1]) if len(args) > 1 else ""
                scheme = uri.split(":", 1)[0].lower() if ":" in uri else ""
                patch_name = slot.split(":", 1)[1] if slot.startswith("patch:") else None
                valid_slot = (re.fullmatch(r"[A-Za-z0-9_-]+", patch_name) is not None
                              if patch_name is not None
                              else identity.valid_asset_slot(slot))
                git_target = (patch_name is not None and patch_name in device.patches
                              and device.patches[patch_name]["git"])
                ok = scheme in ("http", "https", "file") and valid_slot and not git_target
                self.log(device, f"fetch {uri} {slot}")
                if ok:
                    self.queue_fetch(device, source, uri, slot)
                else:
                    builder = osc_message_builder.OscMessageBuilder(address="/os/fetched")
                    builder.add_arg(slot, arg_type="s")
                    builder.add_arg("err", arg_type="s")
                    self.sock.sendto(builder.build().dgram,
                                     (source[0], self.args.report_port))
            elif member in ("reboot", "shutdown", "restart-engine", "updatebopos",
                            "checkout", "patch", "addpatch", "pullpatch",
                            "droppatch", "dropassets"):
                self.admin_verb(device, member, list(args), source)
            elif member == "report":
                self.send_report(device, source)
            elif member == "probe" and args:
                what = str(args[0])
                values = device.reports.get(what)
                if values is None:
                    values = {
                        "id": (int(device.device_id),),
                        "uid": (str(device.mac),),
                        "version": (str(device.version),),
                        "update_model": ("ephemeral" if device.ephemeral else "persistent",),
                    }.get(what)
                if values is not None:
                    builder = osc_message_builder.OscMessageBuilder(address="/os/probe")
                    builder.add_arg(int(device.device_id), arg_type="i")
                    builder.add_arg(what, arg_type="s")
                    for value in values:
                        builder.add_arg(value)
                    self.sock.sendto(builder.build().dgram,
                                     (source[0], self.args.report_port))

    def display(self):
        now = time.monotonic()
        print("\033[H\033[2J", end="")
        print("ID   HOSTNAME       MAC                STATE          VER      GAIN   GAIN2  BACK   OUT  IDENT HB AGE  LAST COMMAND")
        for device in self.devices:
            age = "-" if device.last_hb is None else f"{now - device.last_hb:.1f}s"
            print(
                f"{device.device_id:4g} {device.hostname:14.14} {device.mac:17} "
                f"{device.display_state():14.14} {str(device.version):7.7} "
                f"{device.gain:6g} {device.gain2:6g} {device.backing:6g} "
                f"{'on' if device.output_enabled else 'off':4} "
                f"{'IDENT' if device.ident_until > now else '-':5} {age:7} {device.last_command}"
            )
        sys.stdout.flush()
        self.schedule(0.5, self.display)

    def run(self):
        for index, device in enumerate(self.devices):
            phase = 0.0 if len(self.devices) == 1 else 2.0 * index / (len(self.devices) - 1)
            self.schedule(phase, self.heartbeat, device)
            self.schedule(1.0, self.promote_running, device)
            self.log(device, f"state={device.display_state()}")
        if self.tty:
            print("\033[?25l", end="", flush=True)
            self.schedule(0.0, self.display)

        try:
            while self.running:
                now = time.monotonic()
                while self.events and self.events[0][0] <= now:
                    _when, _order, callback, values = heapq.heappop(self.events)
                    callback(*values)
                    now = time.monotonic()
                timeout = min(0.5, max(0.0, self.events[0][0] - now)) if self.events else 0.5
                readable, _, _ = select.select([self.sock], [], [], timeout)
                if readable:
                    self.receive()
        except KeyboardInterrupt:
            pass
        finally:
            for device in self.devices:
                generator = getattr(device, "param_generator", None)
                if generator is not None:
                    generator.close()
            self.sock.close()
            if self.tty:
                print("\033[?25h\n", end="", flush=True)


def format_token(value):
    return f"{value:g}" if isinstance(value, (int, float)) else str(value)


def load_devices(args):
    identities = []
    if args.devices_file:
        with open(args.devices_file, newline="", encoding="utf-8") as source:
            rows = csv.reader(source, skipinitialspace=True)
            next(rows, None)
            for row in rows:
                if len(row) >= 3 and len(identities) < args.devices:
                    identities.append((row[0].strip(), row[1].strip(), float(row[2])))
        if len(identities) < args.devices:
            raise ValueError(f"devices file contains only {len(identities)} usable rows")
    else:
        for index in range(1, args.devices + 1):
            identities.append((f"02:53:49:4d:{(index >> 8) & 255:02x}:{index & 255:02x}",
                               f"sim{index}", float(index)))

    first_unresponsive = len(identities) - args.unresponsive
    first_unassigned = len(identities) - args.unassigned
    first_wired = len(identities) - args.wired
    first_engine_dead = len(identities) - args.engine_dead
    first_ephemeral = len(identities) - args.ephemeral
    version = args.version
    devices = [Device(mac, hostname, -1 if index >= first_unassigned else device_id,
                      version, index >= first_unresponsive, index >= first_wired,
                      index >= first_engine_dead, index >= first_ephemeral)
               for index, (mac, hostname, device_id) in enumerate(identities)]
    if args.protocol == "v1" and args.state_dir:
        for device in devices:
            device.load_assignment(args.state_dir)
    return devices


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devices", type=int, default=5)
    parser.add_argument("--drop", type=float, default=0.0)
    parser.add_argument("--jitter-ms", type=float, default=0.0)
    parser.add_argument("--unresponsive", type=int, default=0)
    parser.add_argument("--unassigned", type=int, default=0)
    parser.add_argument("--wired", type=int, default=0)
    parser.add_argument("--engine-dead", type=int, default=0)
    parser.add_argument("--ephemeral", type=int, default=0)
    parser.add_argument("--state-dir")
    parser.add_argument("--devices-file")
    parser.add_argument("--hb-interval", type=float, default=10.0)
    parser.add_argument("--boot-secs", type=float, default=15.0)
    parser.add_argument("--fetch-seconds", type=float, default=0.9,
                        help="simulated duration of one patch/asset fetch")
    parser.add_argument("--target", default="255.255.255.255")
    parser.add_argument("--report-port", type=int, default=5550)
    parser.add_argument("--cmd-port", type=int, default=6660)
    parser.add_argument("--protocol", choices=("v1",), default="v1")
    parser.add_argument("--manifest",
                        help="bopos.patch.json served on /os/params (default: patches/demo-pd)")
    parser.add_argument("--patches-dir", default=PATCHES_DIR,
                        help="host patch root used for simulated content fingerprints")
    parser.add_argument("--assets-dir", default=ASSETS_DIR,
                        help="host asset root used for simulated content fingerprints")
    parser.add_argument("--sync-skew-ms", type=float, default=0.0,
                        help="max abs fake clock skew vs leader, random +/- per device")
    parser.add_argument("--sync-jitter-ms", type=float, default=0.0,
                        help="per-pong measurement noise added to deviceTime")
    parser.add_argument("--version", default=None)
    args = parser.parse_args()
    counts = (args.unresponsive, args.unassigned, args.wired, args.engine_dead, args.ephemeral)
    if args.devices < 0 or any(value < 0 or value > args.devices for value in counts):
        parser.error("device counts must satisfy 0 <= count <= devices")
    if not 0.0 <= args.drop <= 1.0:
        parser.error("--drop must be between 0 and 1")
    if (args.jitter_ms < 0 or args.hb_interval <= 0 or args.boot_secs < 0
            or args.fetch_seconds < 0
            or args.sync_skew_ms < 0 or args.sync_jitter_ms < 0):
        parser.error("timing values must be non-negative (heartbeat interval must be positive)")
    if args.version is None:
        args.version = "a1b2c3d"
    if not re.fullmatch(r"[0-9a-fA-F]{1,7}", args.version):
        parser.error("v1 --version must be a hexadecimal short-SHA-looking value")
    args.version = args.version.lower().zfill(7)
    return args


def main():
    global PATCHES_DIR
    args = parse_args()
    PATCHES_DIR = os.path.realpath(args.patches_dir)
    try:
        devices = load_devices(args)
    except (OSError, ValueError) as error:
        raise SystemExit(f"simfleet: {error}") from error
    SimFleet(args, devices).run()


if __name__ == "__main__":
    main()
