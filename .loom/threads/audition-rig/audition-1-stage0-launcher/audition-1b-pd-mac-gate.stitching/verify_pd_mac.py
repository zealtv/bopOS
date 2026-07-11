#!/usr/bin/env python3
"""Real three-instance macOS PD check for the audition local engine surface."""

import os
from pathlib import Path
import select
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
PYTHON = Path.home() / ".venvs" / "bopos" / "bin" / "python"
CMD_PORT = 16660
REPORT_PORT = 15550
ENGINE_PORT_BASE = 17661


def listener(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", port))
    sock.setblocking(False)
    return sock


def packet(address, *args):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


def collect(sockets, seconds):
    captured = []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        readable, _, _ = select.select(sockets, [], [], 0.2)
        for sock in readable:
            data, source = sock.recvfrom(65535)
            try:
                message = osc_message.OscMessage(data)
            except (osc_message.ParseError, ValueError, IndexError):
                continue
            captured.append((sock.getsockname()[1], message.address,
                             list(message.params), source))
    return captured


def assert_ports_bound(ports):
    for port in ports:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            raise AssertionError(f"engine port {port} was not bound")
        finally:
            probe.close()


def main():
    report = listener(REPORT_PORT)
    command = [
        str(PYTHON), str(AUDITION), "--devices", "3",
        "--bind", "127.0.0.1", "--target", "127.0.0.1",
        "--report-port", str(REPORT_PORT), "--cmd-port", str(CMD_PORT),
        "--engine-port-base", str(ENGINE_PORT_BASE),
        "--audio-backend", "coreaudio", "--hb-interval", "1",
        "--catchup-secs", "0.5", "--stop-timeout", "3",
    ]
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True,
                               start_new_session=True)
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        captured = collect([report], 5)
        heartbeats = [entry for entry in captured
                      if entry[0] == REPORT_PORT and entry[1] == "/hb"]
        uids = {entry[2][0] for entry in heartbeats}
        ids = {int(entry[2][1]) for entry in heartbeats}
        assert uids == {"audition-0001", "audition-0002", "audition-0003"}, uids
        assert ids == {1, 2, 3}, ids
        assert_ports_bound(range(ENGINE_PORT_BASE, ENGINE_PORT_BASE + 3))

        target = ("127.0.0.1", CMD_PORT)
        sender.sendto(packet("/all/p/gain", 0.2), target)
        sender.sendto(packet("/2/os/master", 0.4), target)
        sender.sendto(packet("/all/os/mute", 0), target)
        sender.sendto(packet("/all/os/identify"), target)
        for offset in range(3):
            local = ("127.0.0.1", ENGINE_PORT_BASE + offset)
            sender.sendto(packet("/cue", "snap"), local)
            sender.sendto(packet("/pt", 0, 0, 0.5), local)

        collect([report], 2)
    finally:
        sender.close()
        report.close()
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
        try:
            output, _ = process.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate(timeout=3)
        print(output, end="")

    assert process.returncode == 0, process.returncode
    assert "BOPOS_ENGINE_PORT: no such object" not in output
    assert "oscparse" not in output.lower()
    print("PASS: 3 PD engines, bound local ports, distinct heartbeats, clean launcher stop")


if __name__ == "__main__":
    main()
