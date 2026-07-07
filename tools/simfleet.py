#!/usr/bin/env python3
"""Simulated bopOS fleet speaking the currently deployed OSC wire protocol.

N fake devices heartbeat on 5550 and answer dashboard commands on 6660 exactly
as a real Pi does today (PD bopos.osc.pd + helper.py together, seen from the
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
import heapq
import itertools
import random
import select
import socket
import sys
import time

from pythonosc import osc_message, osc_message_builder


class LegacyProtocol:
    """The OSC byte boundary for bopOS's pre-v1 wire protocol."""

    @staticmethod
    def decode(datagram):
        message = osc_message.OscMessage(datagram)
        address = [part for part in message.address.split("/") if part]
        return address + list(message.params)

    @staticmethod
    def matches(selector, device_id):
        if selector == "all":
            return True
        try:
            return float(selector) == float(device_id)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def report(device_id, payload):
        builder = osc_message_builder.OscMessageBuilder(address="/rpt")
        builder.add_arg(float(device_id), arg_type="f")
        for value in payload:
            if isinstance(value, bool):
                builder.add_arg(int(value), arg_type="i")
            elif isinstance(value, (int, float)):
                builder.add_arg(float(value), arg_type="f")
            else:
                builder.add_arg(str(value), arg_type="s")
        return builder.build().dgram

    def heartbeat(self, device):
        return (
            self.report(device.wire_id(), ["hb"]),
            self.report(device.wire_id(), ["version", device.version]),
        )


class Device:
    def __init__(self, mac, hostname, device_id, version, unresponsive=False):
        self.mac = mac
        self.hostname = hostname
        self.device_id = device_id
        self.version = version
        self.unresponsive = unresponsive
        self.state = "booting"
        self.gain = 0.0
        self.gain2 = 0.0
        self.backing = 0.0
        self.echo = False
        self.active_patch = ""
        self.last_hb = None
        self.last_command = "-"

    def wire_id(self):
        # list prepend 0 in bopos.osc.pd: reports carry id 0 until helper config lands
        return 0.0 if self.state == "booting" else self.device_id

    def match_id(self):
        # route-by-id's creation arg: an unconfigured device *listens* on -1, not 0
        return -1.0 if self.state == "booting" else self.device_id

    def display_state(self):
        return "unresponsive" if self.unresponsive and self.state != "off" else self.state


class SimFleet:
    def __init__(self, args, devices):
        self.args = args
        self.devices = devices
        self.protocol = LegacyProtocol()
        self.events = []
        self.sequence = itertools.count()
        self.running = True
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

    def report(self, device, payload):
        self.queue_datagram(self.protocol.report(device.wire_id(), payload))

    def heartbeat(self, device, reschedule=True):
        if device.state in ("booting", "running"):
            hb, version = self.protocol.heartbeat(device)
            self.queue_datagram(hb, device)
            self.queue_datagram(version)
        if reschedule:
            self.schedule(self.args.hb_interval, self.heartbeat, device)

    def promote_running(self, device):
        if device.state == "booting":
            self.set_state(device, "running")

    def announce(self, device):
        # loadbang -> delay 1000 -> aloha in bopos.osc.pd
        if device.state in ("booting", "running"):
            self.report(device, ["aloha", 1])

    def finish_boot(self, device, bump_version=False):
        if bump_version:
            device.version += 1
        device.echo = False
        self.set_state(device, "booting")
        self.schedule(1.0, self.promote_running, device)
        self.schedule(1.2, self.announce, device)
        self.schedule(0.0, self.heartbeat, device, False)

    def reboot_after_silence(self, device, bump_version=False):
        duration = self.args.boot_secs * random.uniform(0.7, 1.3)
        self.set_state(device, "rebooting")
        self.schedule(duration, self.finish_boot, device, bump_version)

    def helper_action(self, device, args):
        if not args:
            return
        verb = str(args[0])
        rest = args[1:]
        if verb == "reboot":
            self.schedule(0.5, self.report, device, ["helper-reply", "reboot"])
            self.schedule(0.5, self.reboot_after_silence, device)
        elif verb == "shutdown":
            self.schedule(0.5, self.report, device, ["helper-reply", "shutdown"])
            self.schedule(0.5, self.set_state, device, "off")
        elif verb == "update":
            self.schedule(0.5, self.report, device, ["helper-reply", "update"])
            self.set_state(device, "updating")
            self.schedule(5.0, self.reboot_after_silence, device, True)
        elif verb == "patch" and rest:
            device.active_patch = str(rest[0])
            self.report(device, ["helper-reply", "update"])
            self.set_state(device, "updating")
            self.schedule(5.0, self.reboot_after_silence, device, False)
        elif verb == "addpatch" and len(rest) >= 2:
            self.schedule(1.0, self.report, device,
                          ["helper-reply", "addpatch", rest[1]])
        elif verb == "getsamples":
            self.report(device, ["helper-reply", "getsamples"])
        elif verb == "restart-engine":
            self.schedule(0.5, self.report, device,
                          ["helper-reply", "restart-engine"])

    def command(self, device, payload):
        device.last_command = " ".join(format_token(item) for item in payload) or "-"
        self.log(device, f"command={device.last_command}")
        if device.unresponsive or device.state not in ("booting", "running") or not payload:
            return

        command = str(payload[0])
        args = payload[1:]
        echo_before = device.echo
        if command in ("gain", "gain2", "backing") and args:
            try:
                setattr(device, command, float(args[0]))
            except (TypeError, ValueError):
                pass
        elif command == "echo" and args:
            try:
                device.echo = bool(float(args[0]))
            except (TypeError, ValueError):
                pass
        elif command == "aloha":
            self.report(device, ["aloha", 1])
        elif command == "id" and args:
            try:
                device.device_id = float(args[0])
            except (TypeError, ValueError):
                pass
        # NB: no `version` handler — on real devices `route version -> s version`
        # has no receiver, so the command is a no-op on the wire today
        elif command == "helper":
            self.helper_action(device, args)

        if echo_before:
            self.report(device, payload)

    def receive(self):
        while True:
            try:
                datagram, _source = self.sock.recvfrom(65535)
            except BlockingIOError:
                return
            try:
                tokens = self.protocol.decode(datagram)
            except Exception:
                continue
            if not tokens:
                continue
            selector, payload = tokens[0], tokens[1:]
            for device in self.devices:
                # each device has its own radio: drop inbound independently,
                # so an /all command can reach some devices and miss others
                if random.random() < self.args.drop:
                    continue
                if self.protocol.matches(selector, device.match_id()):
                    self.command(device, payload)

    def display(self):
        now = time.monotonic()
        print("\033[H\033[2J", end="")
        print("ID   HOSTNAME       MAC                STATE          VER  GAIN   GAIN2  BACK   ECHO  HB AGE  LAST COMMAND")
        for device in self.devices:
            age = "-" if device.last_hb is None else f"{now - device.last_hb:.1f}s"
            print(
                f"{device.device_id:4g} {device.hostname:14.14} {device.mac:17} "
                f"{device.display_state():14.14} {device.version:4g} "
                f"{device.gain:6g} {device.gain2:6g} {device.backing:6g} "
                f"{'on' if device.echo else 'off':5} {age:7} {device.last_command}"
            )
        sys.stdout.flush()
        self.schedule(0.5, self.display)

    def run(self):
        for index, device in enumerate(self.devices):
            phase = 0.0 if len(self.devices) == 1 else 2.0 * index / (len(self.devices) - 1)
            self.schedule(phase, self.heartbeat, device)
            self.schedule(1.0, self.promote_running, device)
            self.schedule(1.2, self.announce, device)
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
    return [Device(mac, hostname, device_id, float(args.version), index >= first_unresponsive)
            for index, (mac, hostname, device_id) in enumerate(identities)]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devices", type=int, default=5)
    parser.add_argument("--drop", type=float, default=0.0)
    parser.add_argument("--jitter-ms", type=float, default=0.0)
    parser.add_argument("--unresponsive", type=int, default=0)
    parser.add_argument("--devices-file")
    parser.add_argument("--hb-interval", type=float, default=10.0)
    parser.add_argument("--boot-secs", type=float, default=15.0)
    parser.add_argument("--target", default="255.255.255.255")
    parser.add_argument("--report-port", type=int, default=5550)
    parser.add_argument("--cmd-port", type=int, default=6660)
    # deployed PD never sets `value version`, so real devices report version 0
    parser.add_argument("--version", type=float, default=0.0)
    args = parser.parse_args()
    if args.devices < 0 or args.unresponsive < 0 or args.unresponsive > args.devices:
        parser.error("device counts must satisfy 0 <= unresponsive <= devices")
    if not 0.0 <= args.drop <= 1.0:
        parser.error("--drop must be between 0 and 1")
    if args.jitter_ms < 0 or args.hb_interval <= 0 or args.boot_secs < 0:
        parser.error("timing values must be non-negative (heartbeat interval must be positive)")
    return args


def main():
    args = parse_args()
    try:
        devices = load_devices(args)
    except (OSError, ValueError) as error:
        raise SystemExit(f"simfleet: {error}") from error
    SimFleet(args, devices).run()


if __name__ == "__main__":
    main()
