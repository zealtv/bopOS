#!/usr/bin/env python3
"""Adversarial exact-UID device-mute checks for helper and simulator."""

import json
import os
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "python" / "bopos.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
sys.path[:0] = [str(ROOT / "python"), str(ROOT / "tools")]

import pyOSC3  # noqa: E402


class FakeServer:
    def __init__(self, _target):
        self.handlers = {}

    def addMsgHandler(self, address, callback):
        self.handlers[address] = callback

    def close(self):
        pass


class FakeClient:
    def __init__(self):
        self.sent = []

    def connect(self, _target):
        pass

    def send(self, message):
        self.sent.append(pyOSC3.decodeOSC(message.getBinary()))


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
sys.argv = ["bopos.py", "unknown"]

import bopos  # noqa: E402
from store import Store  # noqa: E402
from simfleet import ContractProtocol, Device, SimFleet  # noqa: E402
from pythonosc.osc_message import OscMessage  # noqa: E402
from pythonosc.osc_message_builder import OscMessageBuilder  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def helper_packet(address, *args):
    message = pyOSC3.OSCMessage(address)
    for value in args:
        message.append(value)
    return message.getBinary()


def protocol_packet(address, *args):
    builder = OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


class ReplySocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))


class Node:
    def __init__(self, root, uid):
        self.uid = uid
        self.id = -1
        self.version = "abc1234"
        self.update_model = "persistent"
        self.config = {"AUDIO_CHANNELS": "2", "MIXER_CONTROL": None}
        self.store = Store(os.path.join(root, uid, "store"))
        stored = self.store.get("device_muted")
        self.device_muted = bool(stored and stored[0] in (1, True))
        self.fleet_muted = False
        self.mixer_control = None
        self.muted_via_stop = False
        self.groups = ()
        self.elements = []
        self.reports = {}
        self.reports_lock = threading.Lock()


class DatagramQueue:
    def __init__(self):
        self.frames = []

    def sendto(self, data, target):
        self.frames.append((data, target))

    def close(self):
        pass


def decoded(frames):
    return [(OscMessage(data).address, list(OscMessage(data).params))
            for data, _target in frames]


def helper_checks():
    with tempfile.TemporaryDirectory(prefix="bopos-device-mute-helper-") as root:
        first = Node(root, "node-a")
        second = Node(root, "node-b")
        enforced = []
        original_enforce = bopos.enforce_mute
        bopos.enforce_mute = lambda value, state=None: enforced.append(
            (state.uid, bool(value))) or True
        try:
            reply_a, reply_b = ReplySocket(), ReplySocket()
            exact = helper_packet("/all/os/to", "node-b", "mute", 1)
            handled_a = bopos.handle_lan_datagram(
                exact, ("10.0.0.8", 4000), reply_a, first)
            handled_b = bopos.handle_lan_datagram(
                exact, ("10.0.0.8", 4000), reply_b, second)
            check("exact UID isolates two devices sharing id -1",
                  handled_a and handled_b and not first.device_muted
                  and second.device_muted and not reply_a.calls
                  and len(reply_b.calls) == 1, repr((reply_a.calls, reply_b.calls)))
            check("receipt follows persistence and enforcement with both layers",
                  second.store.get("device_muted") == [1]
                  and enforced == [("node-b", True)]
                  and reply_b.calls[0][0] == ["/os/mute", ",sii", "node-b", 1, 1],
                  repr((enforced, reply_b.calls)))

            # Fleet overlay is session-only and release restores UID intent.
            enforced.clear()
            bopos.set_mute(1, second)
            reply = ReplySocket()
            bopos.set_device_mute(0, reply, "10.0.0.8", second)
            check("device unmute under fleet overlay remains effectively muted",
                  second.device_muted is False and second.fleet_muted is True
                  and reply.calls[0][0] == ["/os/mute", ",sii", "node-b", 0, 1]
                  and enforced == [("node-b", True), ("node-b", True)],
                  repr((enforced, reply.calls)))
            bopos.set_mute(0, second)
            check("fleet release restores the persistent UID layer",
                  bopos.effective_mute(second) is False
                  and enforced[-1] == ("node-b", False), repr(enforced))

            # Persist true, reconstruct node state, and report both facts.
            reply = ReplySocket()
            bopos.set_device_mute(1, reply, "10.0.0.8", second)
            restarted = Node(root, "node-b")
            check("node persistent device mute survives restart",
                  restarted.device_muted is True and restarted.fleet_muted is False)
            report_reply = ReplySocket()
            bopos.report_reply(report_reply, "10.0.0.8", restarted)
            report = json.loads(report_reply.calls[0][0][2])
            check("node report exposes device and effective mute separately",
                  report["device_muted"] is True and report["muted"] is True,
                  repr(report))

            # A failed hardware boundary must not issue a false receipt.
            bopos.enforce_mute = lambda _value, state=None: False
            failed_reply = ReplySocket()
            handled = bopos.set_device_mute(0, failed_reply, "10.0.0.8", restarted)
            check("failed hardware enforcement emits no convergence receipt",
                  not handled and not failed_reply.calls)
            invalid_reply = ReplySocket()
            handled = bopos.set_device_mute(2, invalid_reply, "10.0.0.8", restarted)
            check("invalid full-state value is rejected without receipt",
                  not handled and not invalid_reply.calls)
        finally:
            bopos.enforce_mute = original_enforce


def simulator_checks():
    with tempfile.TemporaryDirectory(prefix="bopos-device-mute-sim-") as state_dir:
        devices = [Device("node-a", "a", -1, "abc1234"),
                   Device("node-b", "b", -1, "abc1234")]
        for device in devices:
            device.state = "running"
        args = SimpleNamespace(
            cmd_port=0, target="127.0.0.1", report_port=5550,
            state_dir=state_dir, sync_skew_ms=0.0, drop=0.0,
            jitter_ms=0.0, hb_interval=.5, boot_secs=.1,
            manifest=None, patches_dir=str(ROOT / "patches"),
            assets_dir=str(ROOT / "assets"), fetch_seconds=.1,
        )
        # Exercise the real receive/UID handlers without binding a UDP port.
        fleet = SimFleet.__new__(SimFleet)
        fleet.args = args
        fleet.devices = devices
        fleet.protocol = ContractProtocol()
        fleet.tty = False
        queue = DatagramQueue()
        fleet.sock = queue
        source = ("127.0.0.1", 16660)

        fleet.receive_contract(protocol_packet(
            "/all/os/to", "node-b", "mute", 1), source)
        check("simulator exact UID also isolates multiple id=-1 devices",
              not devices[0].device_muted and devices[1].device_muted
              and decoded(queue.frames) == [("/os/mute", ["node-b", 1, 1])],
              repr(decoded(queue.frames)))
        queue.frames.clear()
        fleet.receive_contract(protocol_packet("/all/os/mute", 1), source)
        fleet.receive_contract(protocol_packet(
            "/all/os/to", "node-b", "mute", 0), source)
        check("simulator models fleet-overlay OR in receipt",
              devices[1].fleet_muted and not devices[1].device_muted
              and devices[1].muted
              and decoded(queue.frames) == [("/os/mute", ["node-b", 0, 1])],
              repr(decoded(queue.frames)))
        fleet.receive_contract(protocol_packet("/all/os/mute", 0), source)
        check("simulator fleet release restores each device layer",
              not devices[0].muted and not devices[1].muted)

        restored = Device("node-b", "b", -1, "abc1234")
        restored.load_assignment(state_dir)
        check("simulator device mute persistence round-trips its state file",
              restored.device_muted is False)
        # Persist true and reconstruct once more to prove the positive state.
        fleet.receive_contract(protocol_packet(
            "/all/os/to", "node-b", "mute", 1), source)
        restored = Device("node-b", "b", -1, "abc1234")
        restored.load_assignment(state_dir)
        check("simulator restart restores a true persistent UID mute",
              restored.device_muted is True and restored.muted is True)
        fleet.sock.close()


def main():
    helper_checks()
    simulator_checks()
    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
