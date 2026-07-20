#!/usr/bin/env python3
"""Browser-free relay verification for audition parameter automation."""

import importlib.util
import json
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "tools" / "audition.py").is_file():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = repo_root()
sys.path[:0] = [str(ROOT / "python"), str(ROOT / "tools")]

from pythonosc import osc_message, osc_message_builder


def load_audition():
    path = ROOT / "tools" / "audition.py"
    spec = importlib.util.spec_from_file_location("audition_automation_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def udp_socket(port=0, timeout=0.35):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", port))
    sock.settimeout(timeout)
    return sock


def contiguous_receivers(count):
    probe = udp_socket()
    base = probe.getsockname()[1]
    probe.close()
    while base <= 65535 - count:
        receivers = []
        try:
            for offset in range(count):
                receivers.append(udp_socket(base + offset))
            return base, receivers
        except OSError:
            for receiver in receivers:
                receiver.close()
            base += count
    raise RuntimeError("could not reserve contiguous UDP receiver ports")


def packet(address, *args):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


def decode(datagram):
    message = osc_message.OscMessage(datagram)
    return message.address, list(message.params)


def scalar_near(frame, address, value):
    return (frame[0] == address and len(frame[1]) == 1
            and isinstance(frame[1][0], (int, float))
            and abs(frame[1][0] - value) < 1e-5)


def receive(receiver, timeout=0.35):
    receiver.settimeout(timeout)
    return decode(receiver.recvfrom(65535)[0])


def drain(receiver, duration=0.08):
    frames = []
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        try:
            frames.append(receive(receiver, min(0.02, deadline - time.monotonic())))
        except socket.timeout:
            pass
    return frames


def frames_until(receiver, predicate, timeout=0.8):
    frames = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            frame = receive(receiver, max(0.01, deadline - time.monotonic()))
        except socket.timeout:
            break
        frames.append(frame)
        if predicate(frame):
            break
    return frames


checks = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" -- {detail}" if detail and not condition else ""))
    checks.append((label, bool(condition)))


audition = load_audition()

with tempfile.TemporaryDirectory(prefix="bopos-audition-automation-") as temp:
    patch_dir = Path(temp, "fixture")
    patch_dir.mkdir()
    (patch_dir / "entry.fake").write_text("fixture\n")
    (patch_dir / "bopos.patch.json").write_text(json.dumps({
        "engine": "fake",
        "entrypoint": "entry.fake",
        "params": [
            {"name": "level", "type": "f", "default": 0},
            {"name": "steps", "type": "i", "default": 0},
            {"path": ["filter", "left"], "name": "cutoff", "type": "f",
             "default": 0},
            {"name": "label", "type": "s"},
        ],
    }))
    reports = udp_socket()
    command_probe = udp_socket()
    command_port = command_probe.getsockname()[1]
    command_probe.close()
    engine_base, engines = contiguous_receivers(3)
    args = audition.parse_args([
        "--devices", "3", "--no-engine", "--bind", "127.0.0.1",
        "--target", "127.0.0.1", "--report-port", str(reports.getsockname()[1]),
        "--cmd-port", str(command_port), "--engine-port-base", str(engine_base),
        "--manifest", str(patch_dir / "bopos.patch.json"),
        "--patches-dir", temp, "--hb-interval", "30", "--catchup-secs", "0",
    ])
    rig = audition.AuditionRig(args)
    runner = threading.Thread(target=rig.run, name="audition-verifier-rig")
    runner.start()
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(address, *values):
        sender.sendto(packet(address, *values), ("127.0.0.1", command_port))

    try:
        # Initial /id frames prove the command loop is live; discard them.
        for engine in engines:
            frames_until(engine, lambda frame: frame[0] == "/id")
            drain(engine, 0.03)

        expected = packet("/p/level", 0.25)
        send("/1/p/level", 0.25)
        raw, _source = engines[0].recvfrom(65535)
        check("plain numeric set stays byte-equivalent", raw == expected,
              repr((decode(raw), decode(expected))))
        check("seat selector reaches exactly one node",
              not drain(engines[1]) and not drain(engines[2]))

        send("/1/p/level", 0.0, 1.0, "120ms")
        fade = frames_until(
            engines[0], lambda frame: frame[0] == "/p/level"
            and len(frame[1]) == 1 and abs(frame[1][0] - 1.0) < 1e-6)
        check("fade emits only numeric scalar/ramp primitives and reaches target",
              bool(fade) and all(frame[0] == "/p/level"
                                 and len(frame[1]) in (1, 2)
                                 and all(isinstance(value, (int, float))
                                         for value in frame[1])
                                 for frame in fade)
              and any(len(frame[1]) == 2 for frame in fade)
              and abs(fade[-1][1][0] - 1.0) < 1e-6, repr(fade))

        send("/all/p/level", "lfo", "saw", 0.0, 1.0, "200ms", "p:0")
        lfos = [frames_until(engine, lambda _frame: False, 0.13) for engine in engines]
        numeric = [[frame for frame in node_frames if frame[0] == "/p/level"]
                   for node_frames in lfos]
        check("LFO expands to multiple numeric frames, never grammar tokens",
              all(len(node_frames) >= 2 and all(
                  len(frame[1]) == 2
                  and all(isinstance(value, (int, float)) for value in frame[1])
                  for frame in node_frames) for node_frames in numeric), repr(numeric))
        first_values = [node_frames[0][1][0] for node_frames in numeric]
        check("non-free LFO phase is aligned across node-local engines",
              max(first_values) - min(first_values) < 0.02, repr(first_values))

        # Replacing node 1 must not disturb the other nodes' independent slots.
        for engine in engines:
            drain(engine, 0.03)
        send("/1/p/level", 0.4)
        node_one = frames_until(engines[0], lambda frame: scalar_near(frame, "/p/level", 0.4))
        node_two = frames_until(engines[1], lambda frame: frame[0] == "/p/level", 0.12)
        check("each node owns independent generator slot state",
              any(scalar_near(frame, "/p/level", 0.4) for frame in node_one)
              and any(len(frame[1]) == 2 for frame in node_two),
              repr((node_one, node_two)))

        send("/2/p/level", "stop")
        stopped = frames_until(engines[1], lambda frame: len(frame[1]) == 1)
        drain(engines[1], 0.07)
        send("/2/p/level", 0.6)
        replaced = frames_until(
            engines[1], lambda frame: scalar_near(frame, "/p/level", 0.6))
        after_replace = drain(engines[1], 0.08)
        check("stop and subsequent plain value replace generator immediately",
              any(len(frame[1]) == 1 for frame in stopped)
              and any(scalar_near(frame, "/p/level", 0.6) for frame in replaced)
              and not after_replace, repr((stopped, replaced, after_replace)))

        send("/3/p/steps", 0, 3, "150ms")
        integer = frames_until(
            engines[2], lambda frame: frame == ("/p/steps", [3]), 0.5)
        crossings = [frame[1][0] for frame in integer if frame[0] == "/p/steps"]
        check("integer crossings use shared paramgen semantics",
              crossings == [0, 1, 2, 3], repr(crossings))

        send("/all/os/groups", "audition-0002", 7)
        time.sleep(0.04)
        drain(reports, 0.03)
        send("/all/p/level", 0.5)
        for engine in engines:
            frames_until(engine, lambda frame: scalar_near(frame, "/p/level", 0.5))
            drain(engine, 0.03)
        send("/g7/p/level", 0.7)
        group_frames = [frames_until(engine, lambda frame: scalar_near(frame, "/p/level", 0.7),
                                     0.12) for engine in engines]
        check("group selector reaches exactly its members",
              not group_frames[0]
              and any(scalar_near(frame, "/p/level", 0.7) for frame in group_frames[1])
              and not group_frames[2], repr(group_frames))

        send("/1/p/level", 1.0, "bad-unit")
        malformed = drain(engines[0], 0.08)
        send("/1/p/level", 0.8)
        recovered = frames_until(
            engines[0], lambda frame: scalar_near(frame, "/p/level", 0.8))
        check("malformed numeric grammar is dropped without killing rig",
              not malformed and runner.is_alive()
              and any(scalar_near(frame, "/p/level", 0.8) for frame in recovered),
              repr((malformed, recovered)))

        send("/1/p/filter/left/cutoff", 0.3)
        nested = frames_until(
            engines[0], lambda frame: scalar_near(frame, "/p/filter/left/cutoff", 0.3))
        send("/1/p/label", "blue")
        label = frames_until(engines[0], lambda frame: frame == ("/p/label", ["blue"]))
        send("/1/p/custom/path", "opaque", 9)
        custom = frames_until(
            engines[0], lambda frame: frame == ("/p/custom/path", ["opaque", 9]))
        check("nested, nonnumeric, and undeclared parameters preserve relay behavior",
              bool(nested) and bool(label) and bool(custom),
              repr((nested, label, custom)))
    finally:
        workers = [node.param_generator._thread for node in rig.nodes
                   if node.param_generator is not None
                   and node.param_generator._thread is not None]
        rig.running = False
        try:
            send("/all/p/level", 0.0)
        except OSError:
            pass
        runner.join(timeout=3)
        sender.close()
        reports.close()
        for engine in engines:
            engine.close()

    check("rig shutdown leaves no generator worker alive",
          not runner.is_alive() and workers and not any(worker.is_alive() for worker in workers),
          repr([(worker.name, worker.is_alive()) for worker in workers]))

passed = sum(result for _label, result in checks)
print(f"\n{passed}/{len(checks)} checks passed")
if passed != len(checks):
    raise SystemExit(1)
