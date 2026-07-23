#!/usr/bin/env python3
"""Focused positive Device enabled protocol, persistence, and migration checks."""

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
sys.path[:0] = [
    str(ROOT / "python"), str(ROOT / "tools"), str(ROOT / "dashboard")]

import pyOSC3  # noqa: E402


class FakeServer:
    def __init__(self, _target):
        self.handlers = {}

    def addMsgHandler(self, address, callback):
        self.handlers[address] = callback

    def close(self):
        pass


class FakeClient:
    def connect(self, _target):
        pass

    def send(self, _message):
        pass


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
sys.argv = ["bopos.py", "unknown"]

import bopos  # noqa: E402
import device_aliases  # noqa: E402
from state import InstallationState  # noqa: E402
from store import Store  # noqa: E402
from simfleet import ContractProtocol, Device, SimFleet  # noqa: E402
from pythonosc.osc_message import OscMessage  # noqa: E402
from pythonosc.osc_message_builder import OscMessageBuilder  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""))
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
        stored = self.store.get("device_enabled")
        self.device_enabled = bool(stored[0]) if stored else True
        self.mute_all = False
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
    with tempfile.TemporaryDirectory(prefix="bopos-device-enabled-helper-") as root:
        first = Node(root, "node-a")
        second = Node(root, "node-b")
        enforced = []
        original_enforce = bopos.enforce_mute
        bopos.enforce_mute = lambda value, state=None: enforced.append(
            (state.uid, bool(value))) or True
        try:
            reply_a, reply_b = ReplySocket(), ReplySocket()
            exact = helper_packet("/all/os/to", "node-b", "enabled", 0)
            handled_a = bopos.handle_lan_datagram(
                exact, ("10.0.0.8", 4000), reply_a, first)
            handled_b = bopos.handle_lan_datagram(
                exact, ("10.0.0.8", 4000), reply_b, second)
            check(
                "exact UID disable isolates two unassigned devices",
                handled_a and handled_b and first.device_enabled
                and not second.device_enabled and not reply_a.calls
                and reply_b.calls[0][0]
                == ["/os/enabled", ",sii", "node-b", 0, 0],
                repr((reply_a.calls, reply_b.calls)))
            check(
                "disable persists before acknowledged mixer enforcement",
                second.store.get("device_enabled") == [0]
                and enforced == [("node-b", True)],
                repr((second.store.get("device_enabled"), enforced)))

            enforced.clear()
            bopos.set_mute(1, second)
            reply = ReplySocket()
            bopos.set_device_enabled(1, reply, "10.0.0.8", second)
            check(
                "MUTE ALL stays independent from Device enabled",
                second.device_enabled and second.mute_all
                and not bopos.output_enabled(second)
                and reply.calls[0][0]
                == ["/os/enabled", ",sii", "node-b", 1, 0],
                repr((enforced, reply.calls)))
            bopos.set_mute(0, second)
            check(
                "MUTE ALL release exposes enabled output",
                bopos.output_enabled(second)
                and enforced[-1] == ("node-b", False),
                repr(enforced))

            report_reply = ReplySocket()
            bopos.report_reply(report_reply, "10.0.0.8", second)
            report = json.loads(report_reply.calls[0][0][2])
            check(
                "report uses positive v1.10 output fields",
                report["contract_version"] == "1.10"
                and report["device_enabled"] is True
                and report["mute_all"] is False
                and report["output_enabled"] is True
                and "device_muted" not in report and "muted" not in report,
                repr(report))

            bopos.enforce_mute = lambda _value, state=None: False
            failed_reply = ReplySocket()
            handled = bopos.set_device_enabled(
                0, failed_reply, "10.0.0.8", second)
            check(
                "failed hardware enforcement emits no false receipt",
                not handled and not failed_reply.calls)
        finally:
            bopos.enforce_mute = original_enforce


def migration_checks():
    legacy = {
        "node-a": {
            "alias": "Finn Jet", "source": "custom", "generator": 2,
            "device_muted": True,
        },
    }
    cleaned = device_aliases.clean_registry(legacy)
    check(
        "host registry migration inverts legacy mute once",
        cleaned == {
            "node-a": {
                "alias": "Finn Jet", "source": "custom", "generator": 2,
                "device_enabled": False,
            },
        },
        repr(cleaned))

    with tempfile.TemporaryDirectory(prefix="bopos-enabled-migration-") as root:
        path = os.path.join(root, "installation.json")
        with open(path, "w", encoding="utf-8") as target:
            json.dump({
                "schema": 1, "name": "migration", "seats": {},
                "device_registry": legacy,
            }, target)
        state = InstallationState(path)
        with open(path, encoding="utf-8") as source:
            saved = json.load(source)
        check(
            "host migration immediately saves only canonical enabled state",
            saved["device_registry"] == cleaned
            and "device_muted" not in saved["device_registry"]["node-a"],
            repr(saved["device_registry"]))

        original_root = bopos.BOPOS_DIR
        bopos.BOPOS_DIR = root
        store = Store(os.path.join(root, "state", "store"))
        store.put("device_muted", [1])
        try:
            node = bopos.NodeState(["bopos.py", "node-a"])
        finally:
            bopos.BOPOS_DIR = original_root
        check(
            "node boot migrates and deletes the legacy persistence key",
            node.device_enabled is False
            and node.store.get("device_enabled") == [0]
            and node.store.get("device_muted") == [],
            repr((node.device_enabled, node.store.get("device_enabled"),
                  node.store.get("device_muted"))))


def simulator_checks():
    with tempfile.TemporaryDirectory(prefix="bopos-device-enabled-sim-") as state_dir:
        devices = [
            Device("node-a", "a", -1, "abc1234"),
            Device("node-b", "b", -1, "abc1234"),
        ]
        for device in devices:
            device.state = "running"
        args = SimpleNamespace(
            cmd_port=0, target="127.0.0.1", report_port=5550,
            state_dir=state_dir, sync_skew_ms=0.0, drop=0.0,
            jitter_ms=0.0, hb_interval=.5, boot_secs=.1,
            manifest=None, patches_dir=str(ROOT / "patches"),
            assets_dir=str(ROOT / "assets"), fetch_seconds=.1,
        )
        fleet = SimFleet.__new__(SimFleet)
        fleet.args = args
        fleet.devices = devices
        fleet.protocol = ContractProtocol()
        fleet.tty = False
        queue = DatagramQueue()
        fleet.sock = queue
        source = ("127.0.0.1", 16660)

        fleet.receive_contract(protocol_packet(
            "/all/os/to", "node-b", "enabled", 0), source)
        check(
            "simulator exact UID and receipt match the positive grammar",
            devices[0].device_enabled and not devices[1].device_enabled
            and decoded(queue.frames)
            == [("/os/enabled", ["node-b", 0, 0])],
            repr(decoded(queue.frames)))
        queue.frames.clear()
        fleet.receive_contract(protocol_packet("/all/os/mute", 1), source)
        fleet.receive_contract(protocol_packet(
            "/all/os/to", "node-b", "enabled", 1), source)
        check(
            "simulator keeps MUTE ALL independent",
            devices[1].device_enabled and devices[1].mute_all
            and not devices[1].output_enabled
            and decoded(queue.frames)
            == [("/os/enabled", ["node-b", 1, 0])],
            repr(decoded(queue.frames)))

        restored = Device("node-b", "b", -1, "abc1234")
        restored.load_assignment(state_dir)
        check(
            "simulator persistence round-trips Device enabled",
            restored.device_enabled is True)


def main():
    helper_checks()
    migration_checks()
    simulator_checks()
    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
