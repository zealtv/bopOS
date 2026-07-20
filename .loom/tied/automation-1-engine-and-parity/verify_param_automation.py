#!/usr/bin/env python3
"""Browser-free verification for parameter automation and simfleet parity."""

import json
import os
import random
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "tools" / "simfleet.py").is_file():
            return candidate
    raise RuntimeError("could not locate repository root")


REPO = repo_root()
sys.path[:0] = [str(REPO / "python"), str(REPO / "tools")]

from paramgen import GeneratorEngine, ParamGrammarError, parse_message
from pythonosc import osc_message_builder


FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def rejects(args, param_type="f"):
    try:
        parse_message(args, param_type)
        return False
    except ParamGrammarError:
        return True


class Synced:
    def __init__(self, offset=0, synced=True):
        self.value = offset
        self.is_synced = synced

    def offset(self):
        return self.value

    def synced(self):
        return self.is_synced


def wait_until(predicate, timeout=0.8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


# A1. Parser grammar.
check("one numeric parses as set", parse_message([0.25], "f").kind == "set")
check("two-element current fade", parse_message([1, "250ms"], "f").kind == "fade")
explicit = parse_message([0, 1, "10s"], "f")
check("three-element explicit fade", explicit.kind == "fade" and explicit.start == 0)
check("even destination/duration list",
      len(parse_message([1, 10, 2, "1.5m"], "f").segments) == 2)
check("loop form", parse_message(["loop", 1, 10, 2, 10], "f").kind == "loop")
check("short loop ignored",
      parse_message(["loop", 1, 10], "f").kind == "fade"
      and parse_message(["loop", 1], "f").kind == "set")
check("stop form", parse_message(["stop"], "i").kind == "stop")
check("all duration units",
      [parse_message([1, value], "f").segments[0][1]
       for value in ("250ms", "10s", "1.5m", "2h")]
      == [250.0, 10000.0, 90000.0, 7200000.0])
short = parse_message(["lfo", "tri", 0, 1, "1s", "p:0.25", "f", "c:-1"], "f")
long = parse_message(["lfo", "drift", -1, 1, 500, "curve:2", "phase:1", "free"], "f")
check("short option spellings any order",
      short.kind == "lfo" and short.phase == 0.25 and short.free and short.curve == -1)
check("long option spellings", long.phase == 1 and long.free and long.curve == 2)
check("all lfo shapes accepted",
      all(parse_message(["lfo", shape, 0, 1, 100], "f").shape == shape
          for shape in ("sine", "tri", "saw", "square", "sh", "drift")))
check("odd segment list rejected", rejects([1, 10, 2, 10, 3]))
check("bad duration units rejected", rejects([1, "3fortnights"]))
check("phase/free misplaced rejected",
      rejects([1, 10, "p:0.5"]) and rejects([1, 10, "free"]))
check("unknown keyword and option rejected",
      rejects(["wobble", 1]) and rejects(["lfo", "sine", 0, 1, 10, "wat"]))
check("curve option rejected on a constant", rejects([1, "c:2"]))


# A2. Generator behavior on its real scheduler thread.
events = []
engine = GeneratorEngine(lambda identity, args: events.append((identity, args)), Synced())
try:
    engine.apply("linear", parse_message([0, 2, 70], "f"), {"type": "f"})
    wait_until(lambda: any(identity == "linear" and args == [2.0]
                           for identity, args in events))
    linear = [args for identity, args in events if identity == "linear"]
    check("float fade is decomposed to progressive scalar engine frames",
          len(linear) >= 3 and linear[0] == [0.0]
          and all(len(args) == 1 for args in linear)
          and all(left[0] <= right[0] for left, right in zip(linear, linear[1:])),
          repr(linear))
    check("completed float fade becomes constant emission",
          any(identity == "linear" and args == [2.0] for identity, args in events),
          repr(events))

    before = len(events)
    engine.apply("curve", parse_message([0, 1, 120, "c:2"], "f"), {"type": "f"})
    wait_until(lambda: any(identity == "curve" and args == [1.0]
                           for identity, args in events[before:]))
    curved = [args for identity, args in events[before:] if identity == "curve"]
    check("curved fade is decomposed to scalar control ticks",
          len(curved) >= 4 and all(len(args) == 1 for args in curved), repr(curved))

    before = len(events)
    engine.apply("up", parse_message([0, 5, 140], "i"), {"type": "i"})
    wait_until(lambda: any(identity == "up" and args == [5]
                           for identity, args in events[before:]))
    up = [args[0] for identity, args in events[before:] if identity == "up"]
    check("int fade emits every upward crossing once", up == [0, 1, 2, 3, 4, 5], repr(up))

    before = len(events)
    engine.apply("down", parse_message([5, 0, 140], "i"), {"type": "i"})
    wait_until(lambda: any(identity == "down" and args == [0]
                           for identity, args in events[before:]))
    down = [args[0] for identity, args in events[before:] if identity == "down"]
    check("int fade emits every downward crossing once", down == [5, 4, 3, 2, 1, 0],
          repr(down))

    before = len(events)
    engine.apply("loop", parse_message(["loop", 1, 40, 2, 40], "f"),
                 {"type": "f", "default": 0})
    wait_until(lambda: any(identity == "loop" and args == [0.0]
                           for identity, args in events[before:]))
    check("loop snaps back to start",
          any(identity == "loop" and args == [0.0] for identity, args in events[before:]),
          repr(events[before:]))

    engine.apply("freeze", parse_message([0, 10, 300], "f"), {"type": "f"})
    time.sleep(0.07)
    engine.apply("freeze", parse_message(["stop"], "f"), {"type": "f"})
    frozen = engine.current_value("freeze")
    time.sleep(0.08)
    check("stop freezes current computed output",
          0 < frozen < 10 and engine.current_value("freeze") == frozen, str(frozen))
finally:
    engine.close()


# Accurate current-value accessor with a controllable clock.
clock = [1_000_000_000]
clock_engine = GeneratorEngine(lambda _identity, _args: None, Synced(), lambda: clock[0])
try:
    clock_engine.apply("value", parse_message([0, 10, 100], "f"), {"type": "f"})
    clock[0] += 50_000_000
    check("current_value is accurate mid-fade", abs(clock_engine.current_value("value") - 5) < 1e-6)
    clock[0] += 100_000_000
    check("current_value retains completed destination", clock_engine.current_value("value") == 10)
finally:
    clock_engine.close()


# Clock-anchored and free phase behavior, using the immediate first emission.
lfo_clock = [5_000_000_000]
lfo_events = []
lfo_engine = GeneratorEngine(lambda identity, args: lfo_events.append((identity, args)),
                             Synced(offset=1_000_000_000), lambda: lfo_clock[0])
try:
    sync_spec = parse_message(["lfo", "saw", 0, 1, "1s", "p:0.1"], "f")
    lfo_engine.apply("sync", sync_spec, {"type": "f"})
    first = lfo_events[-1][1]
    lfo_engine.apply("sync", sync_spec, {"type": "f"})
    second = lfo_events[-1][1]
    check("sync LFO re-apply is phase deterministic", first == second, repr((first, second)))
    random.seed(2468)
    free_spec = parse_message(["lfo", "saw", 0, 1, "1s", "f"], "f")
    lfo_engine.apply("free", free_spec, {"type": "f"})
    first_free = lfo_events[-1][1]
    lfo_engine.apply("free", free_spec, {"type": "f"})
    second_free = lfo_events[-1][1]
    check("seeded free LFO chooses a new phase per apply", first_free != second_free,
          repr((first_free, second_free)))
finally:
    lfo_engine.close()


def free_udp_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def packet(address, *args):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


def in_process_wire_output(manifest_text):
    """Sandbox fallback when the host forbids creating loopback UDP sockets."""
    from types import SimpleNamespace
    import simfleet

    device = simfleet.Device("02:00:00:00:00:01", "param-test", 0, "abc1234")
    device.state = "running"
    fleet = object.__new__(simfleet.SimFleet)
    fleet.protocol = simfleet.ContractProtocol()
    fleet.devices = [device]
    fleet.declared_params = {"level", "steps"}
    fleet.param_declarations = simfleet.manifest_declarations(manifest_text)
    fleet.args = SimpleNamespace(drop=0.0, state_dir=None)
    logs = []
    fleet.log = lambda _device, message: logs.append(message)
    device.param_generator = GeneratorEngine(
        lambda member, values: fleet.emit_param(device, member, values),
        simfleet._DeviceSyncState(device))
    try:
        fleet.receive_contract(packet("/all/p/level", 0.25), ("127.0.0.1", 40000))
        fleet.receive_contract(packet("/all/p/level", 0.25, 0.75, "120ms"),
                               ("127.0.0.1", 40000))
        time.sleep(0.16)
        fleet.receive_contract(packet("/all/p/level", "stop"), ("127.0.0.1", 40000))
        fleet.receive_contract(packet("/all/p/steps", "lfo", "tri", 0, 3, "120ms"),
                               ("127.0.0.1", 40000))
        time.sleep(0.1)
        fleet.receive_contract(packet("/all/p/level", 1, "bad-unit"),
                               ("127.0.0.1", 40000))
        fleet.receive_contract(packet("/all/p/level", 0.5), ("127.0.0.1", 40000))
        time.sleep(0.08)
    finally:
        device.param_generator.close()
    return "\n".join(logs)


# B. Real UDP wire through a subprocess simfleet.
with tempfile.TemporaryDirectory(prefix="bopos-paramgen-") as temp:
    manifest_path = Path(temp, "bopos.patch.json")
    manifest_path.write_text(json.dumps({
        "engine": "pd", "entrypoint": "main.pd",
        "params": [
            {"name": "level", "type": "f", "default": 0},
            {"name": "steps", "type": "i", "default": 0},
        ],
    }))
    try:
        command_port = free_udp_port()
        report_port = free_udp_port()
    except PermissionError:
        print("[INFO] loopback UDP unavailable; exercising OSC decoder in-process")
        output = in_process_wire_output(manifest_path.read_text())
    else:
        command = [sys.executable, str(REPO / "tools" / "simfleet.py"),
                   "--devices", "1", "--target", "127.0.0.1",
                   "--cmd-port", str(command_port), "--report-port", str(report_port),
                   "--manifest", str(manifest_path), "--boot-secs", "0"]
        process = subprocess.Popen(command, cwd=REPO, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            time.sleep(1.15)
            sender.sendto(packet("/all/p/level", 0.25), ("127.0.0.1", command_port))
            time.sleep(0.06)
            sender.sendto(packet("/all/p/level", 0.25, 0.75, "120ms"),
                          ("127.0.0.1", command_port))
            time.sleep(0.16)
            sender.sendto(packet("/all/p/level", "stop"), ("127.0.0.1", command_port))
            sender.sendto(packet("/all/p/steps", "lfo", "tri", 0, 3, "120ms"),
                          ("127.0.0.1", command_port))
            time.sleep(0.1)
            sender.sendto(packet("/all/p/level", 1, "bad-unit"),
                          ("127.0.0.1", command_port))
            time.sleep(0.05)
            sender.sendto(packet("/all/p/level", 0.5), ("127.0.0.1", command_port))
            time.sleep(0.12)
        finally:
            sender.close()
            process.send_signal(signal.SIGINT)
            try:
                output, _ = process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                process.terminate()
                output, _ = process.communicate(timeout=3)
    check("simfleet plain-set log format unchanged", "p/level=0.25" in output, output)
    check("simfleet fade reaches destination", "p/level=0.75" in output, output)
    check("simfleet accepts stop and integer LFO",
          "p/steps=" in output and "grammar error" not in "\n".join(
              line for line in output.splitlines() if "p/steps" in line), output)
    check("simfleet grammar error logged and dropped",
          "p/level grammar error:" in output, output)
    check("simfleet remains alive after grammar error",
          output.rfind("p/level=0.5") > output.find("p/level grammar error:"), output)


print(f"\n{len(FAILURES)} failure(s)")
sys.exit(1 if FAILURES else 0)
