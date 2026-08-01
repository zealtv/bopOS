#!/usr/bin/env python3
"""Stage 0 dashboard discovery and manifest acceptance check."""

import json
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

from pythonosc import osc_message, osc_message_builder


def repo_root():
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "tools" / "audition.py").is_file():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = repo_root()
AUDITION = ROOT / "tools" / "audition.py"
sys.dont_write_bytecode = True


def udp_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(3)
    return sock


def packet(address, *args):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


def receive(sock):
    message = osc_message.OscMessage(sock.recvfrom(65535)[0])
    return message.address, list(message.params)


def main():
    reports = udp_socket()
    commands = udp_socket()
    command_port = commands.getsockname()[1]
    commands.close()
    process = subprocess.Popen([
        sys.executable, str(AUDITION), "--devices", "3", "--no-engine",
        "--bind", "127.0.0.1", "--target", "127.0.0.1",
        "--cmd-port", str(command_port),
        "--report-port", str(reports.getsockname()[1]),
        "--hb-interval", "0.2", "--catchup-secs", "0.1",
    ], cwd=ROOT)
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        heartbeats = [receive(reports) for _ in range(3)]
        assert {args[0] for address, args in heartbeats if address == "/hb"} == {
            "audition-0001", "audition-0002", "audition-0003"
        }
        sender.sendto(packet("/2/os/params"), ("127.0.0.1", command_port))
        address, args = receive(reports)
        assert address == "/os/params" and len(args) == 1
        manifest = json.loads(args[0])
        assert manifest["engine"] == "pd"
        assert {param["name"] for param in manifest["params"]} == {
            "gain0", "gain1", "echo"
        }
        assert {param["name"] for param in manifest["params"]
                if param.get("facilitator") is True} == {"gain0", "gain1"}

        reports.settimeout(0.35)
        deadline = time.monotonic() + 0.35
        while time.monotonic() < deadline:
            try:
                extra_address, _extra_args = receive(reports)
            except socket.timeout:
                break
            assert extra_address != "/os/params", (
                "selector-specific params request produced extra reply"
            )
    finally:
        sender.close()
        reports.close()
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=4)
    assert process.returncode == 0
    print("PASS: three dashboard identities and selector-specific manifest declaration")


if __name__ == "__main__":
    main()
