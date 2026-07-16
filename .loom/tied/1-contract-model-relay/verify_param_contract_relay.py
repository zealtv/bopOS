#!/usr/bin/env python3
"""Browser-free verification for nested parameter contract/model/relay."""

import json
import os
import socket
import sys
import tempfile
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
sys.argv = ["verify_param_contract_relay.py", "unknown"]

from python import manifest, relay
from python import bopos
from tools import audition, simfleet


FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def candidate(params):
    return {"engine": "pd", "entrypoint": "main.pd", "params": params,
            "caps": [], "slots": []}


def declaration(path, name="gain", **extra):
    result = {"name": name, "type": "f", **extra}
    if path is not None:
        result["path"] = path
    return result


def validate(params):
    with tempfile.TemporaryDirectory() as root:
        Path(root, "main.pd").touch()
        return manifest.validate(candidate(params), root)


# A. Canonical identity and validation.
flat = declaration(None)
nested_a = declaration(["instrument", "marimba"])
nested_b = declaration(["fx", "reverb"])
check("flat identity compatibility", manifest.qualify_param(flat) == "gain")
check("nested canonical identity",
      manifest.qualify_param(nested_a) == "instrument/marimba/gain")
loaded, error = validate([nested_a, nested_b])
check("duplicate leaves in distinct paths are valid", loaded is not None and error is None,
      str(error))
loaded, error = validate([nested_a, dict(nested_a)])
check("duplicate qualified identity is rejected",
      loaded is None and "duplicate param identity" in error, str(error))

invalid_paths = [
    ("non-list", "fx"), ("empty", [""]), ("dot", ["."]),
    ("dot-dot", [".."]), ("slash", ["fx/reverb"]),
    ("whitespace", ["fx reverb"]), ("OSC pattern", ["fx*"]),
    ("percent substitute", ["fx%2Freverb"]),
]
for label, path in invalid_paths:
    loaded, error = validate([declaration(path)])
    check(f"invalid path rejected: {label}", loaded is None and bool(error), str(error))
loaded, error = validate([declaration([str(index) for index in range(8)])])
check("eight-segment cap includes leaf", loaded is None and "8 segments" in error,
      str(error))
long_segments = ["a" * 40 for _ in range(6)]
loaded, error = validate([declaration(long_segments, name="b" * 40)])
check("255-byte identity cap", loaded is None and "255 bytes" in error, str(error))
loaded, error = validate([declaration(["fx"], group="legacy")])
check("path and legacy group are mutually exclusive",
      loaded is None and "mutually exclusive" in error, str(error))


# B. Shared shaper matrix: selector spelling is opaque at this seam. Group
# matching belongs to the later Seat-group implementation.
values = [0.5, 7, "tail"]
for selector in ("all", "12", "g3"):
    for suffix in (("gain",), ("track1", "fx", "distortion")):
        shaped = relay.shape_provided_term([selector, "p", *suffix], values)
        check(f"shape {selector} {'/'.join(suffix)}",
              shaped == ("/p/" + "/".join(suffix), values), repr(shaped))
check("master remains strict and one-valued",
      relay.shape_provided_term(["all", "os", "master"], values)
      == ("/os/master", [0.5]))
check("nested master is rejected",
      relay.shape_provided_term(["all", "os", "master", "extra"], values) is None)
check("argumentless parameter is rejected",
      relay.shape_provided_term(["all", "p", "gain"], []) is None)


def pyosc3_packet(address, args):
    message = pyOSC3.OSCMessage(address)
    for value in args:
        if isinstance(value, int):
            message.append(value, "i")
        elif isinstance(value, float):
            message.append(value, "f")
        else:
            message.append(value, "s")
    return message.getBinary()


# C. Production helper uses the shared shaper and preserves the complete tail.
captured = []
original_relay = bopos.relay_provided_term
bopos.relay_provided_term = lambda address, args: captured.append((address, args)) or True
state = SimpleNamespace(id=12)
handled = bopos.handle_lan_datagram(
    pyosc3_packet("/12/p/track1/fx/distortion", values),
    ("127.0.0.1", 40000), SimpleNamespace(sendto=lambda *_args: None), state)
bopos.relay_provided_term = original_relay
check("production relay preserves nested address and args",
      handled and captured == [("/p/track1/fx/distortion", values)], repr(captured))


def datagram(address, args):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


class CaptureSocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((data, target))


# D. Audition relay parity through its real relay method.
rig = object.__new__(audition.AuditionRig)
rig.nodes = [SimpleNamespace(device_id=12, engine_port=19001),
             SimpleNamespace(device_id=13, engine_port=19002)]
rig.sock = CaptureSocket()
rig.local_target = "127.0.0.1"
rig.relay(datagram("/12/p/track1/fx/distortion", values), ("127.0.0.1", 40000))
decoded = [(osc_message.OscMessage(data).address,
            list(osc_message.OscMessage(data).params), target)
           for data, target in rig.sock.calls]
check("audition relay matches production address/args",
      decoded == [("/p/track1/fx/distortion", values, ("127.0.0.1", 19001))],
      repr(decoded))


# E. Simfleet retains and reports qualified identities independently.
device = simfleet.Device("02:00:00:00:00:01", "nested", 12, "abc1234")
device.state = "running"
fleet = object.__new__(simfleet.SimFleet)
fleet.protocol = simfleet.ContractProtocol()
fleet.devices = [device]
fleet.declared_params = {"instrument/marimba/gain", "fx/reverb/gain", "flat"}
fleet.args = SimpleNamespace(drop=0.0, state_dir=None)
logs = []
fleet.log = lambda _device, message: logs.append(message)
fleet.receive_contract(datagram("/12/p/instrument/marimba/gain", [0.25]),
                       ("127.0.0.1", 40000))
fleet.receive_contract(datagram("/all/p/fx/reverb/gain", [0.75]),
                       ("127.0.0.1", 40000))
fleet.receive_contract(datagram("/12/p/flat", [1.0]), ("127.0.0.1", 40000))
check("simfleet retains distinct qualified leaves",
      device.params == {"instrument/marimba/gain": 0.25,
                        "fx/reverb/gain": 0.75, "flat": 1.0}, repr(device.params))
check("simfleet reports qualified identities",
      logs == ["p/instrument/marimba/gain=0.25", "p/fx/reverb/gain=0.75",
               "p/flat=1"], repr(logs))


print(f"\n{len(FAILURES)} failure(s)")
sys.exit(1 if FAILURES else 0)
