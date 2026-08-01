#!/usr/bin/env python3
"""Focused browser-free verification for the Seat-group protocol/node seam."""

import json
import os
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "tools" / "simfleet.py").is_file():
            return candidate
    raise RuntimeError("could not locate repository root")


REPO = repo_root()
sys.path[:0] = [str(REPO), str(REPO / "python"), str(REPO / "python" / "io"),
                str(REPO / "tools")]

import pyOSC3
from pythonosc import osc_message, osc_message_builder


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
sys.argv = ["verify_group_protocol_node.py", "unknown"]

import groups as group_protocol
import bopos
import audition
import simfleet
from store import Store


FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def pyosc3_packet(address, *args):
    message = pyOSC3.OSCMessage(address)
    for value in args:
        if type(value) is int:
            message.append(value, "i")
        elif isinstance(value, float):
            message.append(value, "f")
        else:
            message.append(value, "s")
    return message.getBinary()


def packet(address, *args):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


class PyReply:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))


class CaptureSocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((data, target))


class Node:
    def __init__(self, root):
        self.uid = "node-a"
        self.id = 7
        self.version = "abc1234"
        self.update_model = "persistent"
        self.config = {"AUDIO_CHANNELS": "2", "MIXER_CONTROL": None}
        self.store = Store(os.path.join(root, "store"))
        self.store.put("assignment", [7, "stage-left", 1.0, 2.0])
        self.store.put("groups", [1, 4])
        self.elements = [[1.0, 2.0]]
        self.groups = (1, 4)
        self.mixer_control = None
        self.muted_via_stop = False
        self.reports = {}
        self.reports_lock = threading.Lock()


# A. One canonical grammar/parser.
valid = {"g0": 0, "g1": 1, "g27": 27, "g2147483647": 2147483647}
invalid = ("g", "G1", "g01", "g-1", "g+1", "g2147483648", "g１")
check("canonical group selectors", all(group_protocol.group_selector(key) == value
                                        for key, value in valid.items()))
check("invalid group selectors rejected",
      all(group_protocol.group_selector(value) is None for value in invalid))
check("numeric/all compatibility",
      group_protocol.selector_matches("all", -1, ())
      and group_protocol.selector_matches("7", 7, ())
      and group_protocol.selector_matches("-1", -1, ())
      and not group_protocol.selector_matches("07", 7, ()))
check("assigned group match and overlap",
      group_protocol.selector_matches("g1", 7, (1, 4))
      and group_protocol.selector_matches("g4", 7, (1, 4))
      and not group_protocol.selector_matches("g2", 7, (1, 4)))
check("unassigned and empty membership never group-match",
      not group_protocol.selector_matches("g1", -1, (1,))
      and not group_protocol.selector_matches("g1", 7, ()))
check("membership validates and sorts exact int32 IDs",
      group_protocol.group_ids([4, 0, 2]) == (0, 2, 4)
      and all(group_protocol.group_ids(values) is None for values in
              ([1, 1], [-1], [2147483648], [1.0], ["1"], [True])))


# B. Real helper envelope, persistence, receipt/report and relay matrix.
with tempfile.TemporaryDirectory(prefix="bopos-groups-") as root:
    state = Node(root)
    reply = PyReply()
    source = ("10.0.0.8", 4000)
    handled = bopos.handle_lan_datagram(
        pyosc3_packet("/all/os/groups", "node-a", 9, 2), source, reply, state)
    check("real node applies exact full-state replacement sorted",
          handled and state.groups == (2, 9) and state.store.get("groups") == [2, 9])
    check("real receipt is attributable and sorted",
          reply.calls[-1] == (["/os/groups", ",sii", "node-a", 2, 9],
                              ("10.0.0.8", 5550)), repr(reply.calls[-1]))
    check("empty command tail clears complete membership",
          bopos.handle_lan_datagram(pyosc3_packet("/all/os/groups", "node-a"),
                                    source, reply, state)
          and state.groups == () and state.store.get("groups") == [])
    bopos.handle_lan_datagram(pyosc3_packet("/all/os/groups", "node-a", 9, 2),
                              source, reply, state)

    before_calls = len(reply.calls)
    for args in (("other", 3), ("node-a", 3, 3), ("node-a", -1),
                 ("node-a", 1.0)):
        bopos.handle_lan_datagram(pyosc3_packet("/all/os/groups", *args),
                                  source, reply, state)
    check("UID mismatch and invalid/duplicate IDs change nothing",
          state.groups == (2, 9) and state.store.get("groups") == [2, 9]
          and len(reply.calls) == before_calls)

    captured = []
    original_relay = bopos.relay_provided_term
    bopos.relay_provided_term = lambda address, args: captured.append((address, args)) or True
    try:
        for selector in ("all", "7", "g2"):
            bopos.handle_lan_datagram(pyosc3_packet(f"/{selector}/p/gain", 0.25),
                                      source, reply, state)
            bopos.handle_lan_datagram(
                pyosc3_packet(f"/{selector}/p/track1/fx/distortion", 0.5),
                source, reply, state)
        bopos.handle_lan_datagram(pyosc3_packet("/g3/p/gain", 1.0),
                                  source, reply, state)
    finally:
        bopos.relay_provided_term = original_relay
    expected = [('/p/gain', [0.25]), ('/p/track1/fx/distortion', [0.5])] * 3
    check("flat/nested provided terms relay through all, Seat and group",
          captured == expected, repr(captured))

    bopos.report_reply(reply, "10.0.0.8", state)
    report = json.loads(reply.calls[-1][0][2])
    check("real report exposes sorted membership fact", report["groups"] == [2, 9])

    restarted = group_protocol.stored_group_ids(Store(os.path.join(root, "store")).get("groups"))
    check("real membership survives restart", restarted == (2, 9), repr(restarted))

    original_hostname = bopos.set_hostname
    bopos.set_hostname = lambda _name: None
    try:
        old_assignment = state.store.get("assignment")
        old_receipts = len(reply.calls)
        rejected = [
            bopos.handle_lan_datagram(
                pyosc3_packet("/g2/os/assign", "node-a", 8, "leaked-group"),
                source, reply, state),
            bopos.handle_lan_datagram(
                pyosc3_packet("/7/os/assign", "node-a", 8, "leaked-seat"),
                source, reply, state),
            bopos.handle_lan_datagram(
                pyosc3_packet("/g2/os/groups", "node-a", 6),
                source, reply, state),
            bopos.handle_lan_datagram(
                pyosc3_packet("/g2/os/to", "node-a", "unassign"),
                source, reply, state),
        ]
        check("real literal-all/UID envelopes reject generalized selectors",
              not any(rejected) and state.id == 7 and state.groups == (2, 9)
              and state.store.get("assignment") == old_assignment
              and len(reply.calls) == old_receipts)
        check("literal-all same-Seat assignment still works and preserves membership",
              bopos.handle_lan_datagram(
                  pyosc3_packet("/all/os/assign", "node-a", 7, "stage-left", 3.0, 4.0),
                  source, reply, state)
              and state.groups == (2, 9) and state.store.get("groups") == [2, 9])
        check("direct reassign clears membership before new Seat routes",
              bopos.apply_assign(["node-a", 8, "stage-right"], state)
              and state.id == 8 and state.groups == () and state.store.get("groups") == [])
        bopos.apply_groups(["node-a", 5], reply, "10.0.0.8", state)
        check("unassign clears assignment and membership",
              bopos.apply_unassign(state) and state.id == -1 and state.groups == ()
              and state.store.get("groups") == []
              and state.store.get("assignment")[0] == -1)
    finally:
        bopos.set_hostname = original_hostname

    class FailingStore:
        def __init__(self):
            self.values = {"groups": [1, 4], "assignment": [7, "old"]}

        def get(self, key):
            return list(self.values.get(key, []))

        def put(self, key, values):
            if key == "groups":
                return False
            self.values[key] = list(values)
            return True

    failed = Node(root)
    failed.store = FailingStore()
    failed.groups = (1, 4)
    failed_reply = PyReply()
    check("membership persistence failure retains old state with no receipt",
          not bopos.apply_groups(["node-a", 6], failed_reply, "10.0.0.8", failed)
          and failed.groups == (1, 4) and failed.store.get("groups") == [1, 4]
          and not failed_reply.calls)
    check("failed transition cannot expose a new Seat with old groups",
          not bopos.apply_assign(["node-a", 8, "new"], failed)
          and failed.id == 7 and failed.groups == (1, 4))


# C. Simfleet uses the same parser, wire envelope, persistence and transitions.
with tempfile.TemporaryDirectory(prefix="simfleet-groups-") as root:
    device = simfleet.Device("02:00:00:00:00:01", "sim1", 7, "abc1234")
    device.state = "running"
    fleet = object.__new__(simfleet.SimFleet)
    fleet.protocol = simfleet.ContractProtocol()
    fleet.devices = [device]
    fleet.declared_params = {"gain", "track1/fx/distortion"}
    fleet.args = SimpleNamespace(drop=0.0, state_dir=root, report_port=5550,
                                 target="127.0.0.1")
    fleet.sock = CaptureSocket()
    logs = []
    fleet.log = lambda _device, message: logs.append(message)
    fleet.heartbeat = lambda _device, reschedule=False: None
    fleet.receive_contract(packet("/all/os/groups", device.mac, 4, 1),
                           ("127.0.0.1", 4000))
    receipt = osc_message.OscMessage(fleet.sock.calls[-1][0])
    check("simfleet envelope/receipt parity",
          device.groups == (1, 4) and receipt.address == "/os/groups"
          and list(receipt.params) == [device.mac, 1, 4])
    old_save = device.save_assignment
    old_calls = len(fleet.sock.calls)
    device.save_assignment = lambda *_args, **_kwargs: False
    fleet.receive_contract(packet("/all/os/groups", device.mac, 9),
                           ("127.0.0.1", 4000))
    check("simfleet failed persistence retains state with no receipt",
          device.groups == (1, 4) and len(fleet.sock.calls) == old_calls)
    device.save_assignment = old_save
    fleet.receive_contract(packet("/g4/p/track1/fx/distortion", 0.75),
                           ("127.0.0.1", 4000))
    check("simfleet group nested relay matches only members",
          device.params.get("track1/fx/distortion") == 0.75)
    persisted = json.loads(Path(device.state_file(root)).read_text())
    check("simfleet persists membership with assignment", persisted["groups"] == [1, 4])
    fleet.start_monotonic = 0.0
    fleet.send_report(device, ("127.0.0.1", 4000))
    sim_report_message = osc_message.OscMessage(fleet.sock.calls[-1][0])
    check("simfleet report membership parity",
          json.loads(sim_report_message.params[0])["groups"] == [1, 4])
    old_assignment = (device.device_id, device.hostname, list(device.elements), device.groups)
    fleet.receive_contract(packet("/g1/os/assign", device.mac, 8, "leaked-group"),
                           ("127.0.0.1", 4000))
    fleet.receive_contract(packet("/7/os/assign", device.mac, 8, "leaked-seat"),
                           ("127.0.0.1", 4000))
    check("simfleet assignment requires literal all",
          (device.device_id, device.hostname, list(device.elements), device.groups)
          == old_assignment)
    fleet.receive_contract(packet("/all/os/assign", device.mac, 7, "same"),
                           ("127.0.0.1", 4000))
    check("simfleet literal-all same-Seat assignment preserves membership",
          device.hostname == "same" and device.groups == (1, 4))
    fleet.receive_contract(packet("/all/os/assign", device.mac, 8, "different"),
                           ("127.0.0.1", 4000))
    check("simfleet direct reassign clears membership", device.device_id == 8
          and device.groups == ())
    fleet.receive_contract(packet("/all/os/groups", device.mac, 3),
                           ("127.0.0.1", 4000))
    fleet.receive_contract(packet("/all/os/to", device.mac, "unassign"),
                           ("127.0.0.1", 4000))
    check("simfleet unassign clears membership", device.device_id == -1
          and device.groups == ())
    restored = simfleet.Device(device.mac, "seed", 99, "abc1234")
    restored.load_assignment(root)
    check("simfleet restart restores safe transition", restored.device_id == -1
          and restored.groups == ())


# D. Audition virtual nodes speak the same envelope and matching behavior.
rig = object.__new__(audition.AuditionRig)
rig.nodes = [audition.VirtualNode(0, 7, "audition-0001", 19001),
             audition.VirtualNode(1, 8, "audition-0002", 19002)]
rig.sock = CaptureSocket()
rig.local_target = "127.0.0.1"
rig.args = SimpleNamespace(target="127.0.0.1", report_port=5550)
rig.send_id = lambda _node: None
rig.send_matrix = lambda _node: None
rig.send_point_values = lambda *_args: None
rig.send_heartbeat = lambda _node: None
rig.relay(packet("/all/os/groups", "audition-0001", 6, 2),
          ("127.0.0.1", 4000))
receipt = osc_message.OscMessage(rig.sock.calls[-1][0])
check("audition envelope/receipt parity", rig.nodes[0].groups == (2, 6)
      and rig.nodes[1].groups == () and list(receipt.params) == ["audition-0001", 2, 6])
before_calls = len(rig.sock.calls)
rig.relay(packet("/all/os/groups", "audition-0001", 3, 3),
          ("127.0.0.1", 4000))
check("audition invalid membership changes nothing and has no receipt",
      rig.nodes[0].groups == (2, 6) and len(rig.sock.calls) == before_calls)
rig.started = 0.0
rig._load_patch = lambda: (str(REPO / "patches" / "demo-pd"),
                           {"engine": "pd", "caps": []})
rig.send_report(rig.nodes[0], ("127.0.0.1", 4000))
audition_report = osc_message.OscMessage(rig.sock.calls[-1][0])
check("audition report membership parity",
      json.loads(audition_report.params[0])["groups"] == [2, 6])
rig.sock.calls.clear()
rig.relay(packet("/g6/p/track1/fx/distortion", 0.5), ("127.0.0.1", 4000))
forwarded = [(osc_message.OscMessage(data).address,
              list(osc_message.OscMessage(data).params), target)
             for data, target in rig.sock.calls]
check("audition group strips only selector",
      forwarded == [("/p/track1/fx/distortion", [0.5], ("127.0.0.1", 19001))],
      repr(forwarded))
old_assignment = (rig.nodes[0].device_id, rig.nodes[0].name,
                  rig.nodes[0].positions, rig.nodes[0].groups)
rig.relay(packet("/g6/os/assign", "audition-0001", 9, "leaked-group"),
          ("127.0.0.1", 4000))
rig.relay(packet("/7/os/assign", "audition-0001", 9, "leaked-seat"),
          ("127.0.0.1", 4000))
check("audition assignment requires literal all",
      (rig.nodes[0].device_id, rig.nodes[0].name,
       rig.nodes[0].positions, rig.nodes[0].groups) == old_assignment)
rig.relay(packet("/all/os/assign", "audition-0001", 7, "same"),
          ("127.0.0.1", 4000))
check("audition literal-all same-Seat assignment preserves membership",
      rig.nodes[0].name == "same" and rig.nodes[0].groups == (2, 6))
rig.apply_assignment("all", ["audition-0001", 9, "different"])
check("audition direct reassign clears membership", rig.nodes[0].device_id == 9
      and rig.nodes[0].groups == ())
rig.nodes[0].groups = (3,)
rig.uid_admin(rig.nodes[0], "unassign", (), ("127.0.0.1", 4000))
check("audition unassign clears membership and routing", rig.nodes[0].device_id == -1
      and rig.nodes[0].groups == ()
      and not audition.matches("g3", rig.nodes[0].device_id, (3,)))


print(f"\n{len(FAILURES)} failure(s)")
sys.exit(1 if FAILURES else 0)
