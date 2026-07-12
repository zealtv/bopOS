#!/usr/bin/env python3
"""Run several audible bopOS virtual nodes behind one LAN command socket."""

import argparse
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass

from pythonosc import osc_message, osc_message_builder


REPO_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_DIR, "python"))
import manifest as patch_manifest  # noqa: E402
import relay  # noqa: E402
import runcontext  # noqa: E402

DEFAULT_MANIFEST = os.path.join(REPO_DIR, "patches", "default", "bopos.patch.json")
VERSION = "audition-1"


def osc_datagram(address, *args):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in args:
        if isinstance(value, int):
            builder.add_arg(value, arg_type="i")
        else:
            builder.add_arg(str(value), arg_type="s")
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

    def send_heartbeats(self):
        for node in self.nodes:
            packet = osc_datagram("/hb", node.uid, node.device_id, VERSION,
                                  node.engine_alive(self.args.no_engine))
            self.sock.sendto(packet, self.report_target)

    def send_ids(self):
        packet_by_id = [(node, osc_datagram("/id", node.device_id)) for node in self.nodes]
        for node, packet in packet_by_id:
            self.sock.sendto(packet, (self.local_target, node.engine_port))

    def relay(self, datagram, source=None):
        # Engines see only the ratified selector-stripped surface. Framework
        # mute stays below the engines (production mutes the hardware mixer),
        # so /os/mute is deliberately not relayed here.
        try:
            message = osc_message.OscMessage(datagram)
        except (osc_message.ParseError, ValueError, IndexError):
            return
        parts = [part for part in message.address.split("/") if part]
        if len(parts) != 3:
            return
        selector = parts[0]
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
            next_hb = 0.0
            ids_sent = False
            while self.running:
                now = time.monotonic()
                if now >= next_hb:
                    self.send_heartbeats()
                    next_hb = now + self.args.hb_interval
                if not ids_sent and now - self.started >= self.args.catchup_secs:
                    self.send_ids()
                    ids_sent = True
                try:
                    datagram, source = self.sock.recvfrom(65535)
                    self.relay(datagram, source)
                except socket.timeout:
                    pass
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
    if not 1 <= args.id_base <= 2_147_483_647 - args.devices:
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
