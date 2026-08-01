#!/usr/bin/env python3
"""Browser-free relay/listener matrix convergence verification."""

import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time

from pythonosc import osc_message, osc_message_builder

sys.dont_write_bytecode = True


def repo_root():
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "tools" / "audition.py").is_file():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = repo_root()
AUDITION = ROOT / "tools" / "audition.py"
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "dashboard"))
import audition_geometry  # noqa: E402
import audition_matrix  # noqa: E402
from state import InstallationState  # noqa: E402
from osc_bridge import OSCBridge  # noqa: E402


checks = 0


def check(condition, label):
    global checks
    if not condition:
        raise AssertionError(label)
    checks += 1


def close(actual, expected, tolerance=2e-6):
    check(len(actual) == len(expected), f"arity: {actual!r}")
    for got, want in zip(actual, expected):
        check(abs(float(got) - float(want)) <= tolerance,
              f"matrix value {got!r} != {want!r}")


def udp_socket(timeout=1.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(timeout)
    return sock


def free_port():
    sock = udp_socket()
    port = sock.getsockname()[1]
    sock.close()
    return port


def contiguous_sockets(count):
    base = free_port()
    while True:
        sockets = []
        try:
            for offset in range(count):
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(("127.0.0.1", base + offset))
                sock.settimeout(0.8)
                sockets.append(sock)
            return base, sockets
        except OSError:
            for sock in sockets:
                sock.close()
            base += count


def packet(address, *args):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


def receive(sock):
    message = osc_message.OscMessage(sock.recvfrom(65535)[0])
    return message.address, list(message.params)


def receive_address(sock, wanted, timeout=1.5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        sock.settimeout(max(0.01, deadline - time.monotonic()))
        address, args = receive(sock)
        if address == wanted:
            return args
    raise AssertionError(f"did not receive {wanted}")


def drain(sock):
    sock.settimeout(0.01)
    while True:
        try:
            receive(sock)
        except socket.timeout:
            sock.settimeout(0.8)
            return


def assert_no_matching(sock, wanted_address, label, wanted_args=None, timeout=0.18):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        sock.settimeout(max(0.01, deadline - time.monotonic()))
        try:
            address, args = receive(sock)
        except socket.timeout:
            check(True, label)
            return
        if address == wanted_address and (wanted_args is None or args == wanted_args):
            raise AssertionError(label)
    check(True, label)


def geometry_test():
    listener = audition_geometry.Listener(0, 0, 0, 10)
    terms = audition_geometry.terms_for_positions(
        listener, ((0, -1), (1, 0), (0, 1), (-1, 0)))
    close(tuple(term[0] for term in terms), (0, 1, 0, -1))
    close((terms[0][1],), (0.972,))
    close(audition_geometry.element_terms(listener, (0, 0)), (0, 1))
    turned = audition_geometry.Listener(0, 0, 450, 10)
    close(audition_geometry.element_terms(turned, (1, 0)), (0, 0.972))
    for bad in ((0, 0, 0), (0, 0, 0, 0), (0, 0, True, 10),
                (0, 0, float("nan"), 10)):
        try:
            audition_geometry.listener_from_frame(bad)
        except ValueError:
            check(True, f"rejected listener {bad!r}")
        else:
            check(False, f"accepted listener {bad!r}")

    spec = importlib.util.spec_from_file_location("audition_listener_boundary", AUDITION)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    rig = object.__new__(module.AuditionRig)
    rig.listener, rig.nodes = None, []
    frame = (5.0, 4.0, 0.0, 10.0)
    rig.apply_listener(frame, ("192.0.2.1", 1234))
    check(rig.listener is None, "non-loopback listener frame ignored")
    rig.apply_listener(frame, ("127.0.0.1", 1234))
    check(rig.listener == audition_geometry.Listener(*frame), "loopback listener accepted")
    held = rig.listener
    rig.apply_listener((5.0, 4.0), ("127.0.0.1", 1234))
    check(rig.listener is held, "malformed listener retained last valid state")
    for bad in (
        ["audition-0001", 1, "name", 1.0],
        ["audition-0001", 1, "name", float("nan"), 2.0],
        ["audition-0001", True, "name"],
    ):
        check(module.AuditionRig._assignment(bad) is None,
              f"malformed assignment rejected: {bad!r}")


def dashboard_catchup_test():
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "installation.json"
        path.write_text(json.dumps({
            "devices": {"audition-0001": {
                "id": 11, "name": "north", "pos1": [5, 3], "pos2": [6, 4]
            }}
        }))
        state = InstallationState(str(path))
        state.save_debounced = lambda: None
        broadcasts, assignments, requests = [], [], []
        bridge = OSCBridge(state, lambda kind, data: broadcasts.append((kind, data)),
                           0, 0, "127.0.0.1")
        bridge.assign = lambda *args: assignments.append(args)
        bridge.request = lambda *args: requests.append(args)
        bridge.handle("/hb", ["audition-0001", 1, "audition-2", 1], "127.0.0.1")
        check(assignments == [("audition-0001", 11, "north", [[5, 3], [6, 4]])],
              "durable assignment replayed on appearance")
        check(state.devices["audition-0001"]["id"] == 11,
              "advertised id did not overwrite dashboard authority")
        bridge.handle("/hb", ["audition-0001", 1, "audition-2", 1], "127.0.0.1")
        check(len(assignments) == 1, "wrong-id heartbeat replay was rate limited")
        bridge.handle("/hb", ["audition-0001", 11, "audition-2", 1], "127.0.0.1")
        check(len(assignments) == 1, "assignment ack formed no replay loop")
        bridge.handle("/hb", ["new-uid", 7, "audition-2", 1], "127.0.0.1")
        check(state.devices["new-uid"]["id"] == 7, "unknown uid adopted wire id")
        check(len(assignments) == 1, "unknown uid was not assigned from thin air")


def relay_udp_test():
    reports = udp_socket(2.0)
    command_port = free_port()
    base, engines = contiguous_sockets(2)
    proc = subprocess.Popen([
        sys.executable, str(AUDITION), "--devices", "2", "--no-engine",
        "--bind", "127.0.0.1", "--target", "127.0.0.1",
        "--report-port", str(reports.getsockname()[1]),
        "--cmd-port", str(command_port), "--engine-port-base", str(base),
        "--hb-interval", "0.35", "--catchup-secs", "0.08",
    ], cwd=ROOT)
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = ("127.0.0.1", command_port)
    try:
        heartbeats = [receive_address(reports, "/hb") for _ in range(2)]
        check({args[0] for args in heartbeats} == {"audition-0001", "audition-0002"},
              "initial virtual identities")
        check([receive_address(sock, "/id") for sock in engines] == [[1], [2]],
              "initial id catch-up")
        for sock in engines:
            assert_no_matching(sock, "/audition/matrix",
                               "no matrix before listener state", timeout=0.12)

        sender.sendto(packet("/audition/listener", 5.0, 4.0, 0.0, 10.0), target)
        for sock in engines:
            close(receive_address(sock, "/audition/matrix"), audition_matrix.IDENTITY)

        for sock in engines:
            drain(sock)
        sender.sendto(packet("/all/os/assign", "audition-0001", 11, "north", 5.0, 3.0),
                      target)
        check(receive_address(engines[0], "/id") == [11], "matching assignment id")
        close(receive_address(engines[0], "/audition/matrix"), (0.972, 0, 0, 0.972))
        assigned_hb = receive_address(reports, "/hb")
        while assigned_hb[:2] != ["audition-0001", 11]:
            assigned_hb = receive_address(reports, "/hb")
        check(assigned_hb[1] == 11, "assignment heartbeat converged id")
        assert_no_matching(engines[1], "/id", "uid-targeted assignment isolated",
                           wanted_args=[11])

        drain(engines[0])
        sender.sendto(packet("/1/p/gain", 0.25), target)
        assert_no_matching(engines[0], "/p/gain", "old selector retired", timeout=0.15)
        sender.sendto(packet("/11/p/gain", 0.25), target)
        close(receive_address(engines[0], "/p/gain"), (0.25,))

        drain(engines[0])
        sender.sendto(packet("/11/os/assign", "audition-0001", 11, "pair",
                             6.0, 4.0, 4.0, 4.0), target)
        check(receive_address(engines[0], "/id") == [11], "repeat id is idempotent")
        close(receive_address(engines[0], "/audition/matrix"), (0, 0.972, 0.972, 0))

        for sock in engines:
            drain(sock)
        sender.sendto(packet("/11/os/assign", "audition-0001", 12, "bad", 1.0), target)
        time.sleep(0.08)
        sender.sendto(packet("/audition/listener", 5.0, 4.0, 0.0, 2.0), target)
        close(receive_address(engines[0], "/audition/matrix"), (0, 0.5, 0.5, 0))
        close(receive_address(engines[1], "/audition/matrix"), audition_matrix.IDENTITY)
        sender.sendto(packet("/11/p/gain", 0.4), target)
        close(receive_address(engines[0], "/p/gain"), (0.4,))

        drain(engines[1])
        sender.sendto(packet("/all/os/assign", "audition-0002", 0, "zero"), target)
        check(receive_address(engines[1], "/id") == [0], "device id zero accepted")
        close(receive_address(engines[1], "/audition/matrix"), audition_matrix.IDENTITY)
        zero_hb = receive_address(reports, "/hb")
        while zero_hb[:2] != ["audition-0002", 0]:
            zero_hb = receive_address(reports, "/hb")
        check(zero_hb[1] == 0, "device id zero heartbeat")
        sender.sendto(packet("/0/p/gain", 0.6), target)
        close(receive_address(engines[1], "/p/gain"), (0.6,))

        # Heartbeat cadence resends the current complete matrix for engine
        # restart/reconnect catch-up without another listener or position edit.
        sender.sendto(packet("/audition/listener", 5.0, 4.0), target)
        check(receive_address(engines[0], "/id", timeout=0.8) == [11],
              "node 0 id reconnect resend")
        close(receive_address(engines[0], "/audition/matrix", timeout=0.8),
              (0, 0.5, 0.5, 0))
        check(receive_address(engines[1], "/id", timeout=0.8) == [0],
              "node 1 id reconnect resend")
        close(receive_address(engines[1], "/audition/matrix", timeout=0.8),
              audition_matrix.IDENTITY)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=4)
        sender.close()
        reports.close()
        for sock in engines:
            sock.close()
    check(proc.returncode == 0, "relay clean teardown")


def simfleet_observability_test():
    reports = udp_socket(2.0)
    command_port = free_port()
    proc = subprocess.Popen([
        sys.executable, str(ROOT / "tools" / "simfleet.py"), "--devices", "1",
        "--target", "127.0.0.1", "--report-port", str(reports.getsockname()[1]),
        "--cmd-port", str(command_port), "--boot-secs", "0.05",
        "--hb-interval", "0.2",
    ], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        heartbeat = receive_address(reports, "/hb", timeout=2.0)
        uid = heartbeat[0]
        sender.sendto(packet("/all/os/assign", uid, 9, "preview",
                             1.0, 2.0, 3.0, 4.0),
                      ("127.0.0.1", command_port))
        time.sleep(0.25)
    finally:
        proc.send_signal(signal.SIGTERM)
        output, _ = proc.communicate(timeout=4)
        sender.close()
        reports.close()
    check("assigned id=9 name=preview" in output, "simfleet assignment observed")
    check("positions=[[1.0,2.0],[3.0,4.0]]" in output,
          "simfleet ordered preview positions logged")


def main():
    geometry_test()
    dashboard_catchup_test()
    relay_udp_test()
    simfleet_observability_test()
    print(f"preview relay matrix verify: {checks} checks passed")


if __name__ == "__main__":
    main()
