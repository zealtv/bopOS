#!/usr/bin/env python3
"""Run several audible bopOS virtual nodes behind one LAN command socket."""

import argparse
import heapq
import ipaddress
import itertools
import json
import math
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field

from pythonosc import osc_message, osc_message_builder


REPO_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_DIR, "python"))
import manifest as patch_manifest  # noqa: E402
import identity  # noqa: E402
import audition_geometry  # noqa: E402
import audition_matrix  # noqa: E402
import asset_slots  # noqa: E402
import paramgen  # noqa: E402
import pointfield  # noqa: E402
import relay  # noqa: E402
import runcontext  # noqa: E402
import groups as group_protocol  # noqa: E402
import audio_config  # noqa: E402

DEFAULT_MANIFEST = os.path.join(REPO_DIR, "patches", "demo-pd", "bopos.patch.json")
VERSION = "audition-2"
HOSTNAME_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


def osc_datagram(address, *args):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in args:
        if isinstance(value, int):
            builder.add_arg(value, arg_type="i")
        else:
            builder.add_arg(str(value), arg_type="s")
    return builder.build().dgram


def osc_float_datagram(address, values):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in values:
        builder.add_arg(float(value), arg_type="f")
    return builder.build().dgram


def matches(selector, device_id, memberships=()):
    return group_protocol.selector_matches(selector, device_id, memberships)


@dataclass
class VirtualNode:
    index: int
    device_id: int
    uid: str
    engine_port: int
    name: str = ""
    positions: tuple = ()
    points: dict = field(default_factory=dict)
    groups: tuple = ()
    device_enabled: bool = True
    mute_all: bool = False
    master: float = 1.0
    process: subprocess.Popen | None = None
    param_generator: paramgen.GeneratorEngine | None = None
    audio_config: dict = field(default_factory=lambda: {
        "card": "Simulated", "mixer_control": "Master",
        "sample_rate": 44100, "period_size": 512, "nperiods": 2,
    })
    audio_active: dict = field(default_factory=lambda: {
        "card": "Simulated", "mixer_control": "Master",
        "sample_rate": 44100, "period_size": 512, "nperiods": 2,
    })
    audio_status: str = "active"
    audio_error: str | None = None

    def engine_alive(self, no_engine):
        if no_engine:
            return 0
        return int(self.process is not None and self.process.poll() is None)


class AuditionRig:
    def __init__(self, args):
        self.args = args
        self.running = True
        self.started = time.monotonic()
        self.nodes = [
            VirtualNode(i, args.id_base + i, f"audition-{i + 1:04d}",
                        args.engine_port_base + i)
            for i in range(args.devices)
        ]
        _patch_dir, loaded = self._load_patch()
        self.param_declarations = {
            patch_manifest.qualify_param(declaration): declaration
            for declaration in loaded.get("params", [])
        }
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind((args.bind, args.cmd_port))
        self.sock.settimeout(0.1)
        self.local_target = args.engine_host
        self.report_target = (args.target, args.report_port)
        self.listener = None
        self.editor_element = 0
        self.pending_cues = []
        self.pending_events = []
        self.event_sequence = itertools.count()
        for node in self.nodes:
            node.param_generator = paramgen.GeneratorEngine(
                lambda identity, values, target=node: self.send_engine(
                    target, f"/p/{identity}", values),
                None,
            )

    def _load_patch(self):
        cached = getattr(self, "_loaded_patch", None)
        if cached is not None:
            return cached
        path = os.path.realpath(self.args.manifest)
        if os.path.basename(path) != patch_manifest.MANIFEST_NAME:
            raise ValueError("--manifest must name a bopos.patch.json file")
        patch_dir = os.path.dirname(path)
        loaded, error = patch_manifest.load(patch_dir)
        if loaded is None:
            raise ValueError(error)
        self._loaded_patch = (patch_dir, loaded)
        return self._loaded_patch

    def patch_listing(self):
        """Return the host-backed inventory exposed by every virtual node."""
        active_dir, _loaded = self._load_patch()
        active_name = os.path.basename(active_dir)
        listing = []
        try:
            names = sorted(os.listdir(self.args.patches_dir))
        except OSError:
            names = []
        for name in names:
            path = os.path.join(self.args.patches_dir, name)
            if not os.path.isdir(path) or os.path.islink(path):
                continue
            manifest, _error = patch_manifest.load(path)
            if manifest is None:
                continue
            entry = {
                "name": name,
                "active": name == active_name,
                "git": False,
                "manifest": True,
            }
            try:
                # real host directories, so the real identity (contract sec 7, v1.4)
                entry["fingerprint"] = identity.fingerprint(path)
            except OSError:
                pass
            listing.append(entry)
        if not any(item["name"] == active_name for item in listing):
            entry = {"name": active_name, "active": True, "git": False,
                     "manifest": True}
            try:
                entry["fingerprint"] = identity.fingerprint(active_dir)
            except OSError:
                pass
            listing.append(entry)
            listing.sort(key=lambda item: item["name"])
        return listing

    def engine_command(self, node, patch_dir, loaded, context=None):
        entrypoint = os.path.join(patch_dir, loaded["entrypoint"])
        if context is None:
            context = runcontext.generate(os.path.basename(patch_dir),
                                          patches_dir=os.path.dirname(patch_dir),
                                          assets_dir=os.path.join(REPO_DIR, "assets"))
        if self.args.engine_command:
            values = {
                "entrypoint": entrypoint,
                "port": str(node.engine_port),
                "id": str(node.device_id),
            }
            try:
                return [part.format(**values) for part in shlex.split(self.args.engine_command)]
            except KeyError as error:
                allowed = "{entrypoint}, {port}, {id}"
                raise ValueError(
                    f"unknown --engine-command placeholder {error}; allowed: {allowed}"
                ) from error

        engine = self.args.engine or loaded["engine"]
        if engine == "pd":
            backend = []
            if self.args.audio_backend == "coreaudio":
                backend = ["-pa"]
            elif self.args.audio_backend == "jack":
                backend = ["-jack"]
            startup = (
                f"; BOPOS_ENGINE_PORT {node.engine_port}; "
                f"bopos-context seed {context['seed']}; "
                f"bopos-context run-id {context['run_id']}; "
                f"bopos-context patch {os.path.basename(patch_dir)}; "
                f"bopos-context assets {asset_slots.fudi_list(context['assets'])}; "
                f"bopos-context version {context['version']}; "
                f"bopos-context patch-fingerprint {context['patch_fingerprint']}; "
                f"bopos-context groups "
                f"{' '.join(str(g) for g in group_protocol.wire_groups(node.groups))}"
            )
            gui = [] if getattr(self.args, "edit", False) else ["-nogui"]
            return [self.args.pd_bin, *gui, *backend, "-path",
                    os.path.join(REPO_DIR, "pd"), "-open", entrypoint,
                    "-send", startup]
        return [engine, entrypoint]

    def start_engines(self):
        if self.args.no_engine:
            return
        patch_dir, loaded = self._load_patch()
        for node in self.nodes:
            context = runcontext.generate(os.path.basename(patch_dir),
                                          patches_dir=os.path.dirname(patch_dir),
                                          assets_dir=os.path.join(REPO_DIR, "assets"))
            command = self.engine_command(node, patch_dir, loaded, context)
            env = os.environ.copy()
            env.update({
                "BOPOS_ENGINE_PORT": str(node.engine_port),
                "BOPOS_ACTIVEPATCH": os.path.basename(patch_dir),
                "BOPOS_ASSETS": asset_slots.json_list(context["assets"]),
                "BOPOS_AUDITION_ID": str(node.device_id),
                "BOPOS_SEED": str(context["seed"]),
                "BOPOS_RUN_ID": context["run_id"],
                "BOPOS_VERSION": context["version"],
                "BOPOS_PATCH_FINGERPRINT": context["patch_fingerprint"],
                "BOPOS_GROUPS": " ".join(
                    str(g) for g in group_protocol.wire_groups(node.groups)),
            })
            node.process = subprocess.Popen(command, env=env, start_new_session=True)
            print(f"audition: id={node.device_id} port={node.engine_port} "
                  f"pid={node.process.pid}", flush=True)

    def send_heartbeat(self, node):
        packet = osc_datagram("/hb", node.uid, node.device_id, VERSION,
                              node.engine_alive(self.args.no_engine))
        self.sock.sendto(packet, self.report_target)

    def send_report(self, node, source):
        patch_dir, loaded = self._load_patch()
        report = {
            "uid": node.uid,
            "hostname": node.name or node.uid,
            "engine": loaded["engine"],
            "has_i2c": False,
            "has_wifi": False,
            "audio_channels": 2,
            "screen": "screen" in loaded.get("caps", []),
            "patch": os.path.basename(patch_dir),
            "uptime": int(time.monotonic() - self.started),
            "git_rev": VERSION,
            "update_model": "ephemeral",
            "contract_version": "1.14",
            "groups": list(getattr(node, "groups", ())),
            "device_enabled": bool(node.device_enabled),
            "mute_all": bool(node.mute_all),
            "output_enabled": bool(node.device_enabled and not node.mute_all),
            "audio": {
                "configured": dict(node.audio_config),
                "active": dict(node.audio_active),
                "cards": [{
                    "id": "Simulated", "index": 0,
                    "label": "Simulated stereo output",
                    "mixer_controls": ["Master"],
                }],
                "status": node.audio_status,
                "error": node.audio_error,
            },
        }
        self.sock.sendto(osc_datagram("/os/report", json.dumps(report)),
                         (source[0], self.args.report_port))

    def send_rev(self, node, source):
        self.sock.sendto(osc_datagram("/os/rev", VERSION, "ephemeral", node.uid),
                         (source[0], self.args.report_port))

    def uid_admin(self, node, member, args, source):
        allowed = {"identify", "report", "reboot", "shutdown", "restart-engine",
                   "updatebopos", "unassign"}
        if member == "enabled" and len(args) == 1:
            try:
                value = int(args[0])
            except (TypeError, ValueError):
                return
            if value not in (0, 1):
                return
            node.device_enabled = bool(value)
            self.sock.sendto(osc_datagram(
                "/os/enabled", node.uid, value,
                int(node.device_enabled and not node.mute_all)),
                (source[0], self.args.report_port))
            return
        if member == "hostname" and len(args) == 1:
            hostname = str(args[0])
            if HOSTNAME_RE.fullmatch(hostname) is None:
                return
            node.name = hostname
            self.sock.sendto(osc_datagram(
                "/os/hostname", node.uid, hostname, "ok"),
                (source[0], self.args.report_port))
            self.send_heartbeat(node)
            return
        if member == "audio-config" and len(args) == 1:
            cards = [{
                "id": "Simulated", "index": 0,
                "label": "Simulated stereo output",
                "mixer_controls": ["Master"],
            }]
            try:
                candidate = audio_config.validate(json.loads(str(args[0])), cards)
                node.audio_config = candidate
                node.audio_active = dict(candidate)
                node.audio_status = "active"
                node.audio_error = None
                status, phase = "ok", "applied"
            except (ValueError, TypeError) as error:
                node.audio_status = "error"
                node.audio_error = str(error)
                status, phase = "err", "invalid"
            payload = {
                "configured": dict(node.audio_config),
                "active": dict(node.audio_active),
                "cards": cards,
                "status": node.audio_status,
                "error": node.audio_error,
            }
            self.sock.sendto(osc_datagram(
                "/os/audio-config", node.uid, status, phase,
                json.dumps(payload, separators=(",", ":"))),
                (source[0], self.args.report_port))
            return
        if member not in allowed or args:
            return
        if member == "identify":
            self.send_engine(node, "/notify", ("identify",))
        elif member == "report":
            self.send_report(node, source)
        elif member == "unassign":
            node.groups = ()
            node.device_id = -1
            node.positions = ()
            self.send_id(node)
            self.send_groups(node)
            self.send_matrix(node)
            self.send_heartbeat(node)
        else:
            # Audition nodes are ephemeral processes; model attribution without
            # ever applying a destructive host lifecycle action.
            self.send_rev(node, source)

    def send_heartbeats(self):
        for node in self.nodes:
            self.send_heartbeat(node)
            # A periodic full-state resend lets a restarted/reconnected engine
            # converge without requiring another dashboard movement.
            if self.listener is not None:
                self.send_id(node)
            self.send_matrix(node)

    def send_ready(self):
        ready = ((VERSION, "edit") if getattr(self.args, "edit", False)
                 else (VERSION,))
        self.sock.sendto(osc_datagram("/audition/ready", *ready),
                         ("127.0.0.1", self.args.report_port))

    def send_id(self, node):
        self.sock.sendto(osc_datagram("/id", node.device_id),
                         (self.local_target, node.engine_port))

    def matrix_for_node(self, node):
        if not node.positions:
            return audition_matrix.IDENTITY
        if len(node.positions) > 2:
            # The fleet assignment is true-N, but Wave 1 audition is fixed
            # stereo. Preserve assignment state and bypass unsupported shapes.
            return audition_matrix.IDENTITY
        try:
            terms = audition_geometry.terms_for_positions(self.listener, node.positions)
            return audition_matrix.matrix_for_positions(terms)
        except ValueError:
            return audition_matrix.IDENTITY

    def send_matrix(self, node):
        # Before the first valid listener frame the PD adapter's load-time
        # identity is authoritative; silence on this private plane means hold.
        if self.listener is None:
            return
        frame = audition_matrix.matrix_frame(self.matrix_for_node(node))
        self.sock.sendto(osc_float_datagram(frame[0], frame[1:]),
                         (self.local_target, node.engine_port))

    def send_engine(self, node, address, args=()):
        builder = osc_message_builder.OscMessageBuilder(address=address)
        for value in args:
            builder.add_arg(value)
        self.sock.sendto(builder.build().dgram,
                         (self.local_target, node.engine_port))

    @staticmethod
    def effective_master(node):
        """Audition's engine-facing output gate for execution MUTE ALL."""
        return 0.0 if node.mute_all else node.master

    def set_master(self, node, value):
        """Retain requested master while sending its mute-composed value."""
        try:
            node.master = float(value)
        except (TypeError, ValueError):
            return False
        self.send_engine(node, "/os/master", (self.effective_master(node),))
        return True

    def set_mute_all(self, node, value):
        """Apply MUTE ALL without exposing the framework mute verb to engines."""
        node.mute_all = bool(value)
        self.send_engine(node, "/os/master", (self.effective_master(node),))

    def send_groups(self, node):
        # Mirrors bopos.py's send_groups_to_engine: full, sentinel-shaped
        # membership list on every successful membership change (engine
        # group-context amendment, 2026-07-20).
        self.send_engine(node, "/groups", group_protocol.wire_groups(node.groups))

    def send_point_values(self, node, changed, removed=()):
        if not node.positions:
            return
        entries = pointfield.decompose(changed, node.positions)
        if self.args.edit:
            entries = [(point_id, self.editor_element, value)
                       for point_id, _element, value in entries]
            entries += [(point_id, self.editor_element, 0.0)
                        for point_id in sorted(removed)]
        else:
            for point_id in sorted(removed):
                for index in range(len(node.positions)):
                    entries.append((point_id, index, 0.0))
        for point_id, element, value in entries:
            self.send_engine(node, "/pt", (int(point_id), int(element), float(value)))

    def set_editor_element(self, params, source):
        if not self.args.edit or not self._loopback(source) or not params:
            return
        try:
            element = int(params[0])
        except (TypeError, ValueError):
            return
        if element not in (0, 1) or element == self.editor_element:
            return
        previous = self.editor_element
        for node in self.nodes:
            for point_id in sorted(node.points):
                self.send_engine(node, "/pt", (int(point_id), previous, 0.0))
        self.editor_element = element
        for node in self.nodes:
            self.send_point_values(node, node.points)

    def apply_points(self, parts, params):
        parsed = pointfield.parse_wire(parts, params)
        if parsed is None:
            return
        kind, payload = parsed
        for node in self.nodes:
            if kind == "frame":
                removed = set(node.points) - set(payload)
                node.points = dict(payload)
                changed = payload
            elif kind == "set":
                point_id, point = payload
                node.points[point_id] = point
                removed = set()
                changed = {point_id: point}
            else:
                removed = {payload} if payload in node.points else set()
                node.points.pop(payload, None)
                changed = {}
            self.send_point_values(node, changed, removed)

    def schedule_cue(self, params):
        if len(params) < 2:
            return
        try:
            deadline = int(str(params[1]))
        except (TypeError, ValueError):
            return
        heapq.heappush(self.pending_cues, (deadline, str(params[0])))

    def dispatch_due_cues(self):
        now = time.monotonic_ns()
        while self.pending_cues and self.pending_cues[0][0] <= now:
            _deadline, cue_id = heapq.heappop(self.pending_cues)
            for node in self.nodes:
                self.send_engine(node, "/cue", (cue_id,))

    def schedule_event(self, parts, params):
        identity_parts = parts[2:]
        identity = "/".join(identity_parts)
        if (len(identity_parts) > patch_manifest.MAX_PARAM_SEGMENTS
                or any(patch_manifest.PARAM_NAME.fullmatch(part) is None
                       for part in identity_parts)
                or len(identity.encode("ascii")) > patch_manifest.MAX_PARAM_IDENTITY_BYTES
                or not 1 <= len(params) <= patch_manifest.MAX_EVENT_ARITY + 1
                or not isinstance(params[0], str)
                or any(not isinstance(value, float) for value in params[1:])):
            return
        try:
            deadline = int(params[0])
            elements = tuple(float(value) for value in params[1:])
        except (TypeError, ValueError):
            return
        matched = [
            node for node in self.nodes
            if matches(parts[0], node.device_id, getattr(node, "groups", ()))
        ]
        if params[0] == "0":
            for node in matched:
                self.fire_event(node, identity, elements)
            return
        for node in matched:
            heapq.heappush(
                self.pending_events,
                (deadline, next(self.event_sequence), node, identity, elements))

    def dispatch_due_events(self):
        now = time.monotonic_ns()
        while self.pending_events and self.pending_events[0][0] <= now:
            _deadline, _sequence, node, identity, elements = heapq.heappop(
                self.pending_events)
            self.fire_event(node, identity, elements)

    def fire_event(self, node, identity, elements):
        normalized = tuple(float(f"{float(value):.6g}") for value in elements)
        self.send_engine(node, "/e/" + identity, normalized)
        values = " ".join(f"{value:g}" for value in normalized)
        suffix = f" elements={values}" if values else ""
        print(f"audition: id={node.device_id} event {identity} fired "
              f"fire_mono={time.monotonic_ns()}{suffix}", flush=True)

    def send_ids(self):
        for node in self.nodes:
            self.send_id(node)
            self.send_matrix(node)

    @staticmethod
    def _loopback(source):
        if source is None:
            return False
        try:
            return ipaddress.ip_address(source[0]).is_loopback
        except (ValueError, TypeError, IndexError):
            return False

    @staticmethod
    def _assignment(params):
        if len(params) < 3 or not isinstance(params[0], str) or not isinstance(params[2], str):
            return None
        raw_id = params[1]
        if isinstance(raw_id, bool) or not isinstance(raw_id, (int, float)):
            return None
        device_id = int(raw_id)
        if not math.isfinite(float(raw_id)) or float(raw_id) != device_id:
            return None
        if not 0 <= device_id <= 2_147_483_647:
            return None
        flat = params[3:]
        if len(flat) % 2:
            return None
        values = []
        for value in flat:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            value = float(value)
            if not math.isfinite(value):
                return None
            values.append(value)
        positions = tuple((values[index], values[index + 1])
                          for index in range(0, len(values), 2))
        return str(params[0]), device_id, str(params[2]), positions

    def apply_assignment(self, selector, params):
        assignment = self._assignment(params)
        if assignment is None:
            return
        uid, device_id, name, positions = assignment
        for node in self.nodes:
            if (not matches(selector, node.device_id, getattr(node, "groups", ()))
                    or uid != node.uid):
                continue
            if (node.device_id == device_id and node.name == name
                    and node.positions == positions):
                continue
            changing_seat = node.device_id != device_id
            if changing_seat:
                node.groups = ()
            node.device_id = device_id
            node.name = name
            node.positions = positions
            self.send_id(node)
            if changing_seat:
                self.send_groups(node)
            self.send_matrix(node)
            self.send_point_values(node, node.points)
            self.send_heartbeat(node)

    def apply_listener(self, params, source):
        if not self._loopback(source):
            return
        try:
            listener = audition_geometry.listener_from_frame(params)
        except ValueError:
            return
        self.listener = listener
        for node in self.nodes:
            self.send_matrix(node)

    def relay(self, datagram, source=None):
        # Engines see only the ratified selector-stripped surface. Framework
        # mute stays below the engines (production mutes the hardware mixer),
        # so /os/mute is deliberately not relayed here.
        try:
            message = osc_message.OscMessage(datagram)
        except (osc_message.ParseError, ValueError, IndexError):
            return
        parts = [part for part in message.address.split("/") if part]
        if parts == ["audition", "listener"]:
            self.apply_listener(message.params, source)
            return
        if parts == ["audition", "editor-element"]:
            self.set_editor_element(message.params, source)
            return
        if parts == ["cue"]:
            self.schedule_cue(message.params)
            return
        if len(parts) >= 3 and parts[1] == "e":
            self.schedule_event(parts, message.params)
            return
        if parts and parts[0] == "pt":
            self.apply_points(parts, message.params)
            return
        if parts == ["all", "os", "to"]:
            if len(message.params) < 2:
                return
            uid, member = str(message.params[0]), str(message.params[1])
            for node in self.nodes:
                if node.uid == uid:
                    self.uid_admin(node, member, tuple(message.params[2:]), source)
            return
        if parts == ["all", "os", "groups"]:
            if not message.params or not isinstance(message.params[0], str):
                return
            memberships = group_protocol.group_ids(message.params[1:])
            if memberships is None:
                return
            reply_host = source[0] if source is not None else self.args.target
            for node in self.nodes:
                if node.uid != message.params[0]:
                    continue
                node.groups = memberships
                self.send_groups(node)
                self.sock.sendto(osc_datagram("/os/groups", node.uid, *memberships),
                                 (reply_host, self.args.report_port))
            return
        if len(parts) < 3:
            return
        selector = parts[0]
        shaped = relay.shape_provided_term(parts, message.params)
        if shaped is not None:
            address, args = shaped
            if address == "/os/master":
                for node in self.nodes:
                    if matches(selector, node.device_id, getattr(node, "groups", ())):
                        self.set_master(node, args[0])
                return
            if address.startswith("/p/"):
                identity = address[3:]
                declaration = self.param_declarations.get(identity)
                param_type = patch_manifest.param_wire_type(declaration)
                if param_type in ("f", "i"):
                    try:
                        spec = paramgen.parse_message(args, param_type)
                    except paramgen.ParamGrammarError as error:
                        print(f"WARNING: {address} parameter grammar: {error}",
                              flush=True)
                        return
                    for node in self.nodes:
                        if matches(selector, node.device_id,
                                   getattr(node, "groups", ())):
                            node.param_generator.apply(identity, spec, declaration)
                    return
            builder = osc_message_builder.OscMessageBuilder(address=address)
            for value in args:
                builder.add_arg(value)
            forwarded = builder.build().dgram
            for node in self.nodes:
                if matches(selector, node.device_id, getattr(node, "groups", ())):
                    self.sock.sendto(forwarded, (self.local_target, node.engine_port))
            return
        if len(parts) != 3:
            return
        if parts[1:] == ["os", "assign"]:
            if selector == "all":
                self.apply_assignment(selector, message.params)
            return
        if parts[1:] == ["os", "params"]:
            patch_dir, _loaded = self._load_patch()
            manifest_text = patch_manifest.raw(patch_dir)
            if manifest_text is None:
                return
            packet = osc_datagram("/os/params", manifest_text)
            reply_host = source[0] if source is not None else self.args.target
            for node in self.nodes:
                if matches(selector, node.device_id, getattr(node, "groups", ())):
                    self.sock.sendto(packet, (reply_host, self.args.report_port))
            return
        if parts[1:] == ["os", "patches"]:
            packet = osc_datagram("/os/patches", json.dumps(
                self.patch_listing(), separators=(",", ":")))
            reply_host = source[0] if source is not None else self.args.target
            for node in self.nodes:
                if matches(selector, node.device_id, getattr(node, "groups", ())):
                    self.sock.sendto(packet, (reply_host, self.args.report_port))
            return
        if parts[1:] == ["os", "identify"]:
            uid = str(message.params[0]) if message.params else None
            packet = osc_datagram("/notify", "identify")
            for node in self.nodes:
                if (matches(selector, node.device_id, getattr(node, "groups", ()))
                        and uid in (None, node.uid)):
                    self.sock.sendto(packet, (self.local_target, node.engine_port))
            return
        if parts[1:] == ["os", "mute"] and message.params:
            try:
                value = int(message.params[0])
            except (TypeError, ValueError):
                return
            if value not in (0, 1):
                return
            for node in self.nodes:
                if matches(selector, node.device_id, getattr(node, "groups", ())):
                    self.set_mute_all(node, value)
            return

    def stop(self):
        for node in self.nodes:
            if node.param_generator is not None:
                node.param_generator.close()
        descendants = {}
        for node in self.nodes:
            if node.process is not None:
                descendants[node.process.pid] = self._descendant_pids(node.process.pid)
        for node in self.nodes:
            process = node.process
            if process is not None and process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        deadline = time.monotonic() + self.args.stop_timeout
        for node in self.nodes:
            process = node.process
            if process is None:
                continue
            remaining = max(0, deadline - time.monotonic())
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            # Pd's macOS GUI and watchdog may place themselves outside the
            # engine's process group.  They are still this engine's known
            # descendants, so reap that captured set without touching other
            # Pd sessions the operator may have open.
            for pid in descendants.get(process.pid, ()):
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            pending = set(descendants.get(process.pid, ()))
            deadline = time.monotonic() + 1.0
            while pending and time.monotonic() < deadline:
                for pid in tuple(pending):
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        pending.discard(pid)
                    except PermissionError:
                        pending.discard(pid)
                if pending:
                    time.sleep(0.02)
            for pid in pending:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        self.sock.close()

    @staticmethod
    def _descendant_pids(pid):
        found, pending = set(), [pid]
        while pending:
            parent = pending.pop()
            try:
                result = subprocess.run(
                    ["pgrep", "-P", str(parent)], check=False, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            except OSError:
                break
            for value in result.stdout.split():
                try:
                    child = int(value)
                except ValueError:
                    continue
                if child not in found:
                    found.add(child)
                    pending.append(child)
        return found

    def run(self):
        try:
            self.start_engines()
            self.send_ready()
            next_hb = 0.0
            ids_sent = False
            while self.running:
                now = time.monotonic()
                self.dispatch_due_cues()
                self.dispatch_due_events()
                if now >= next_hb:
                    self.send_heartbeats()
                    next_hb = now + self.args.hb_interval
                if not ids_sent and now - self.started >= self.args.catchup_secs:
                    self.send_ids()
                    ids_sent = True
                timeout = 0.1
                if self.pending_cues:
                    until_cue = (self.pending_cues[0][0] - time.monotonic_ns()) / 1e9
                    timeout = max(0.001, min(timeout, until_cue))
                if self.pending_events:
                    until_event = (
                        self.pending_events[0][0] - time.monotonic_ns()) / 1e9
                    timeout = max(0.001, min(timeout, until_event))
                self.sock.settimeout(timeout)
                try:
                    datagram, source = self.sock.recvfrom(65535)
                    self.relay(datagram, source)
                except socket.timeout:
                    pass
                self.dispatch_due_cues()
                self.dispatch_due_events()
        finally:
            self.stop()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devices", type=int, default=3)
    parser.add_argument("--target", default="255.255.255.255")
    parser.add_argument("--report-port", type=int, default=5550)
    parser.add_argument("--cmd-port", type=int, default=6660)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--patches-dir", default=os.path.join(REPO_DIR, "patches"))
    parser.add_argument("--bind", default="")
    parser.add_argument("--id-base", type=int, default=1)
    parser.add_argument("--engine-host", default="127.0.0.1")
    parser.add_argument("--engine-port-base", type=int, default=16661)
    parser.add_argument("--engine", help="override the manifest engine")
    parser.add_argument("--engine-command",
                        help="command template with optional {entrypoint}, {port}, {id}")
    parser.add_argument("--pd-bin", default=(
        "/Applications/Pd-0.55-2.app/Contents/Resources/bin/pd"
        if sys.platform == "darwin" else "pd"))
    parser.add_argument("--audio-backend", choices=("coreaudio", "jack", "none"),
                        default="coreaudio" if sys.platform == "darwin" else "jack")
    parser.add_argument("--no-engine", action="store_true")
    parser.add_argument("--edit", action="store_true",
                        help="launch one patch for editing (PD GUI visible)")
    parser.add_argument("--hb-interval", type=float, default=10.0)
    parser.add_argument("--catchup-secs", type=float, default=1.0)
    parser.add_argument("--stop-timeout", type=float, default=3.0)
    args = parser.parse_args(argv)
    if args.edit:
        args.devices = 1
    if args.devices < 1:
        parser.error("--devices must be at least 1")
    if not 0 <= args.id_base <= 2_147_483_647 - args.devices + 1:
        parser.error("--id-base is outside the int32 device-id range")
    if not 1 <= args.engine_port_base <= 65535 - args.devices + 1:
        parser.error("engine port range exceeds UDP ports")
    if args.hb_interval <= 0 or args.catchup_secs < 0 or args.stop_timeout < 0:
        parser.error("timing values must be non-negative (heartbeat interval positive)")
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        rig = AuditionRig(args)
        signal.signal(signal.SIGINT, lambda _sig, _frame: setattr(rig, "running", False))
        signal.signal(signal.SIGTERM, lambda _sig, _frame: setattr(rig, "running", False))
        rig.run()
    except (OSError, ValueError) as error:
        raise SystemExit(f"audition: {error}") from error


if __name__ == "__main__":
    main()
