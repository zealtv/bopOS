#!/usr/bin/env python3
"""Focused boundary-3 checks for reports, probes, and removed surfaces."""
import os
import socket
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo root")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "python"))

from pyOSC3 import OSCMessage, decodeOSC
from pythonosc import osc_message, osc_message_builder
import bopos as helper
import manifest


class Replies:
    def __init__(self):
        self.items = []

    def sendto(self, datagram, target):
        self.items.append((decodeOSC(datagram), target))


def packet(address, *values):
    message = OSCMessage(address)
    for value in values:
        helper.typed_append(message, value)
    return message.getBinary()


def free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def helper_checks():
    # /admin joined the engine surface with the v1.7 patch-admin-surface
    # amendment (2026-07-17); amended here 2026-07-19 (automation-1 worklog).
    assert sorted(helper.server.callbacks) == ["/admin", "/config", "/load", "/report", "/store"]
    state = helper.node_state
    original_id, original_reports = state.id, state.reports
    state.id, state.reports = 7, {}
    replies = Replies()
    source = ("127.0.0.1", 45678)
    try:
        helper.report_callback(args=["level", 0.25, 3, "ok"])
        assert state.reports["level"] == (0.25, 3, "ok")
        assert helper.handle_lan_datagram(
            packet("/7/os/probe", "level"), source, replies, state)
        decoded, target = replies.items.pop()
        assert str(decoded[0]) == "/os/probe"
        assert [int(decoded[2]), str(decoded[3])] == [7, "level"]
        assert abs(float(decoded[4]) - 0.25) < 1e-6
        assert int(decoded[5]) == 3 and str(decoded[6]) == "ok"
        assert target == ("127.0.0.1", 5550)

        assert helper.handle_lan_datagram(
            packet("/7/os/probe", "uid"), source, replies, state)
        decoded, _target = replies.items.pop()
        assert str(decoded[3]) == "uid" and str(decoded[4]) == state.uid

        assert helper.handle_lan_datagram(
            packet("/7/os/probe", "unknown"), source, replies, state)
        assert not replies.items, "unknown probe unexpectedly replied"
        assert not helper.handle_lan_datagram(
            packet("/8/os/probe", "level"), source, replies, state)
        assert not replies.items, "wrong-selector probe replied"

        helper.report_callback(args=["bad/name", 1])
        helper.report_callback(args=["empty"])
        assert set(state.reports) == {"level"}
    finally:
        state.id, state.reports = original_id, original_reports


def manifest_checks():
    with tempfile.TemporaryDirectory() as directory:
        open(os.path.join(directory, "main.pd"), "w").close()
        with open(os.path.join(directory, "bopos.patch.json"), "w") as target:
            target.write('{"engine":"pd","entrypoint":"main.pd","params":['
                         '{"name":"level","type":"f","role":"meter"}]}')
        loaded, error = manifest.load(directory)
        assert loaded is None and "role was removed" in error


def simfleet_probe_check():
    cmd_port, report_port = free_port(), free_port()
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", report_port))
    receiver.settimeout(4)
    process = subprocess.Popen([
        sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
        "--devices", "1", "--target", "127.0.0.1",
        "--cmd-port", str(cmd_port), "--report-port", str(report_port),
        "--hb-interval", "10", "--boot-secs", "1",
    ], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        time.sleep(0.4)
        builder = osc_message_builder.OscMessageBuilder(address="/1/os/probe")
        builder.add_arg("version", arg_type="s")
        sender.sendto(builder.build().dgram, ("127.0.0.1", cmd_port))
        deadline = time.monotonic() + 4
        while True:
            message = osc_message.OscMessage(receiver.recvfrom(65535)[0])
            if message.address == "/os/probe":
                break
            if time.monotonic() > deadline:
                raise AssertionError("simfleet probe reply timed out")
        assert list(message.params) == [1, "version", "a1b2c3d"]
    finally:
        sender.close()
        receiver.close()
        process.terminate()
        output, _ = process.communicate(timeout=5)
    assert "Traceback" not in output, output


def removed_surface_checks():
    paths = [
        os.path.join(REPO, "python", "bopos.py"),
        os.path.join(REPO, "tools", "simfleet.py"),
        os.path.join(REPO, "dashboard", "osc_bridge.py"),
        os.path.join(REPO, "dashboard", "state.py"),
        os.path.join(REPO, "dashboard", "static", "js", "dashboard.js"),
        os.path.join(REPO, "dashboard", "static", "js", "facilitator.js"),
        os.path.join(REPO, "patches", "demo-pd", "bopos.patch.json"),
    ]
    text = "\n".join(open(path).read() for path in paths)
    for removed in ("meter_loop", "METER_INTERVAL", 'role === "meter"',
                    'role !== "meter"', 'address="/rpt"', 'address == "/rpt"',
                    "helper-reply", "--legacy-reports", "--meter-interval"):
        assert removed not in text, "removed token remains: {}".format(removed)


def main():
    helper_checks()
    manifest_checks()
    simfleet_probe_check()
    removed_surface_checks()
    print("[PASS] 7770 exposes only config/store/load/report")
    print("[PASS] typed engine reports answer selector-gated one-shot probes")
    print("[PASS] simfleet implements the one-shot probe wire shape")
    print("[PASS] meter, role:meter, /rpt, echo-report, and legacy report surfaces removed")
    print("boundary-3 framework slimdown checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
