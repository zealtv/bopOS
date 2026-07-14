#!/usr/bin/env python3
"""Run several audible bopOS virtual nodes behind one LAN command socket."""

import argparse
import heapq
import ipaddress
import math
import os
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
import audition_geometry  # noqa: E402
import audition_matrix  # noqa: E402
import pointfield  # noqa: E402
import relay  # noqa: E402
import runcontext  # noqa: E402

DEFAULT_MANIFEST = os.path.join(REPO_DIR, "patches", "demo-pd", "bopos.patch.json")
VERSION = "audition-2"


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


def matches(selector, device_id):
    if selector == "all":
        return True
    try:
        return int(selector) == device_id and selector == str(device_id)
    except ValueError:
        return False


@dataclass
class VirtualNode:
    index: int
    device_id: int
    uid: str
    engine_port: int
    name: str = ""
    positions: tuple = ()
    points: dict = field(default_factory=dict)
    process: subprocess.Popen | None = None

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
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind((args.bind, args.cmd_port))
        self.sock.settimeout(0.1)
        self.local_target = args.engine_host
        self.report_target = (args.target, args.report_port)
        self.listener = None
        self.pending_cues = []

    def _load_patch(self):
        path = os.path.realpath(self.args.manifest)
        if os.path.basename(path) != patch_manifest.MANIFEST_NAME:
            raise ValueError("--manifest must name a bopos.patch.json file")
        patch_dir = os.path.dirname(path)
        loaded, error = patch_manifest.load(patch_dir)
        if loaded is None:
            raise ValueError(error)
        return patch_dir, loaded

    def engine_command(self, node, patch_dir, loaded, context=None):
        entrypoint = os.path.join(patch_dir, loaded["entrypoint"])
        if context is None:
            context = runcontext.generate(os.path.basename(patch_dir))
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
                f"bopos-context assets {os.path.join(REPO_DIR, 'assets')}"
            )
            return [self.args.pd_bin, "-nogui", *backend, "-path",
                    os.path.join(REPO_DIR, "pd"), "-open", entrypoint,
                    "-send", startup]
        return [engine, entrypoint]

    def start_engines(self):
        if self.args.no_engine:
            return
        patch_dir, loaded = self._load_patch()
        for node in self.nodes:
            context = runcontext.generate(os.path.basename(patch_dir))
            command = self.engine_command(node, patch_dir, loaded, context)
            env = os.environ.copy()
            env.update({
                "BOPOS_ENGINE_PORT": str(node.engine_port),
                "BOPOS_ACTIVEPATCH": os.path.basename(patch_dir),
                "BOPOS_ASSETS": os.path.join(REPO_DIR, "assets"),
                "BOPOS_AUDITION_ID": str(node.device_id),
                "BOPOS_SEED": str(context["seed"]),
                "BOPOS_RUN_ID": context["run_id"],
            })
            node.process = subprocess.Popen(command, env=env, start_new_session=True)
            print(f"audition: id={node.device_id} port={node.engine_port} "
                  f"pid={node.process.pid}", flush=True)

    def send_heartbeat(self, node):
        packet = osc_datagram("/hb", node.uid, node.device_id, VERSION,
                              node.engine_alive(self.args.no_engine))
        self.sock.sendto(packet, self.report_target)

    def send_heartbeats(self):
        for node in self.nodes:
            self.send_heartbeat(node)
            # A periodic full-state resend lets a restarted/reconnected engine
            # converge without requiring another dashboard movement.
            if self.listener is not None:
                self.send_id(node)
            self.send_matrix(node)

    def send_ready(self):
        self.sock.sendto(osc_datagram("/audition/ready", VERSION),
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

    def send_point_values(self, node, changed, removed=()):
        if not node.positions:
            return
        entries = pointfield.decompose(changed, node.positions)
        for point_id in sorted(removed):
            for index in range(len(node.positions)):
                entries.append((point_id, index, 0.0))
        for point_id, element, value in entries:
            self.send_engine(node, "/pt", (int(point_id), int(element), float(value)))

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
            if not matches(selector, node.device_id) or uid != node.uid:
                continue
            if (node.device_id == device_id and node.name == name
                    and node.positions == positions):
                continue
            node.device_id = device_id
            node.name = name
            node.positions = positions
            self.send_id(node)
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
        if parts == ["cue"]:
            self.schedule_cue(message.params)
            return
        if parts and parts[0] == "pt":
            self.apply_points(parts, message.params)
            return
        if len(parts) != 3:
            return
        selector = parts[0]
        if parts[1:] == ["os", "assign"]:
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
                if matches(selector, node.device_id):
                    self.sock.sendto(packet, (reply_host, self.args.report_port))
            return
        if parts[1:] == ["os", "identify"]:
            uid = str(message.params[0]) if message.params else None
            packet = osc_datagram("/notify", "identify")
            for node in self.nodes:
                if matches(selector, node.device_id) and uid in (None, node.uid):
                    self.sock.sendto(packet, (self.local_target, node.engine_port))
            return
        shaped = relay.shape_provided_term(parts, message.params)
        if shaped is None:
            return
        address, args = shaped
        builder = osc_message_builder.OscMessageBuilder(address=address)
        for value in args:
            builder.add_arg(value)
        forwarded = builder.build().dgram
        for node in self.nodes:
            if matches(selector, node.device_id):
                self.sock.sendto(forwarded, (self.local_target, node.engine_port))

    def stop(self):
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
        self.sock.close()

    def run(self):
        try:
            self.start_engines()
            self.send_ready()
            next_hb = 0.0
            ids_sent = False
            while self.running:
                now = time.monotonic()
                self.dispatch_due_cues()
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
                self.sock.settimeout(timeout)
                try:
                    datagram, source = self.sock.recvfrom(65535)
                    self.relay(datagram, source)
                except socket.timeout:
                    pass
                self.dispatch_due_cues()
        finally:
            self.stop()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devices", type=int, default=3)
    parser.add_argument("--target", default="255.255.255.255")
    parser.add_argument("--report-port", type=int, default=5550)
    parser.add_argument("--cmd-port", type=int, default=6660)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
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
    parser.add_argument("--hb-interval", type=float, default=10.0)
    parser.add_argument("--catchup-secs", type=float, default=1.0)
    parser.add_argument("--stop-timeout", type=float, default=3.0)
    args = parser.parse_args(argv)
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
