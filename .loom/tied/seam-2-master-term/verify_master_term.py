#!/usr/bin/env python3
"""Verification for seam-2: master as a provided term (contract sec 4.1).

Real dashboard/server.py + real simfleet, no browser. The dashboard targets
255.255.255.255 (the deployed broadcast+selector model, proven shareable on
Linux by the audition-0 spike), so a SO_REUSEPORT sniffer socket on the sim
command port sees every dashboard->fleet datagram alongside the fleets.

Checks:
  1. a param send carries the raw mix on the wire (no master composition);
  2. a master change emits exactly ONE /all/os/master broadcast and zero
     per-device volume re-sends (resend_volumes is gone);
  3. after the master change, param sends still carry the raw mix;
  4. a late-joining device gets the current master unicast (selector-addressed)
     piggybacked on the params catch-up push, and its sim logs delivery;
  5. every fleet-A device logged the broadcast delivery; no server traceback.

Deps (venv ~/.venvs/bopos): pip install fastapi uvicorn[standard] python-osc websockets
Run:  ~/.venvs/bopos/bin/python verify_master_term.py
"""
import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

import websockets
from pythonosc import osc_message

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent

HTTP_PORT = 18093
REPORT_PORT = 15582
CMD_PORT = 16692
LATE_ID = 7

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def sent(wire, address, value):
    # OSC floats are 32-bit, so 0.6 arrives as 0.6000000238...
    return any(m[0] == address and m[1] and isinstance(m[1][0], float)
               and abs(m[1][0] - value) < 1e-6 for m in wire)


class Sniffer:
    """Every dashboard->fleet datagram, seen exactly as the devices see it."""

    def __init__(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.bind(("", port))
        self.sock.setblocking(False)

    def drain(self):
        messages = []
        while True:
            try:
                datagram, _ = self.sock.recvfrom(65535)
            except BlockingIOError:
                return messages
            try:
                message = osc_message.OscMessage(datagram)
                messages.append((message.address, list(message.params)))
            except Exception:
                pass

    async def collect(self, seconds):
        deadline = time.monotonic() + seconds
        messages = []
        while time.monotonic() < deadline:
            messages.extend(self.drain())
            await asyncio.sleep(0.05)
        return messages


def start_fleet(extra, log):
    return subprocess.Popen(
        [sys.executable, os.path.join(REPO, "tools/simfleet.py"),
         "--protocol", "v1", "--target", "127.0.0.1",
         "--report-port", str(REPORT_PORT), "--cmd-port", str(CMD_PORT),
         "--hb-interval", "1.0", "--boot-secs", "1.0", "--meter-interval", "0",
         ] + extra,
        cwd=REPO, stdout=log, stderr=subprocess.STDOUT)


def read_log(log):
    log.flush()
    with open(log.name) as source:
        return source.read()


async def main():
    fleet_log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    late_log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    server_log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    state_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    late_csv = tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False)
    late_csv.write("mac,hostname,id\n02:53:49:4d:ff:01,simlate,%d\n" % LATE_ID)
    late_csv.flush()

    sniffer = Sniffer(CMD_PORT)
    fleet = start_fleet(["--devices", "2"], fleet_log)
    server = subprocess.Popen([
        sys.executable, os.path.join(REPO, "dashboard/server.py"),
        "--port", str(HTTP_PORT), "--listen-port", str(REPORT_PORT),
        "--send-port", str(CMD_PORT), "--osc-target", "255.255.255.255",
        "--state-file", state_file,
    ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
    late = None
    try:
        await asyncio.sleep(4)  # boot + declare + initial catch-up settle

        async with websockets.connect(f"ws://127.0.0.1:{HTTP_PORT}/ws") as ws:
            state = json.loads(await ws.recv())
            devices = state["data"]["devices"]
            target = next(uid for uid, dev in devices.items() if int(dev["id"]) == 1)

            sniffer.drain()  # discard boot-time traffic

            # 1. raw mix on the wire at master=1
            await ws.send(json.dumps({"type": "set_param",
                                      "data": {"uid": target, "name": "gain", "value": 0.6}}))
            wire = await sniffer.collect(1.0)
            check("param send carries the raw mix",
                  sent(wire, "/1/p/gain", 0.6), f"wire={wire}")

            # 2. master change: one broadcast, no volume re-sends
            await ws.send(json.dumps({"type": "set_master", "data": {"value": 0.5}}))
            wire = await sniffer.collect(1.5)
            masters = [m for m in wire if m[0] == "/all/os/master"]
            resends = [m for m in wire if "/p/" in m[0] or m[0] in ("/1/gain", "/2/gain")]
            check("master change emits exactly one /all/os/master 0.5",
                  len(masters) == 1 and sent(masters, "/all/os/master", 0.5),
                  f"masters={masters}")
            check("no per-device volume re-sends", resends == [], f"resends={resends}")

            # 3. still the raw mix after the master change (no composition)
            await ws.send(json.dumps({"type": "set_param",
                                      "data": {"uid": target, "name": "gain", "value": 0.8}}))
            wire = await sniffer.collect(1.0)
            check("param send after master change is still the raw mix",
                  sent(wire, "/1/p/gain", 0.8),
                  f"gain sends={[m for m in wire if 'gain' in m[0]]}")

            # 4. late joiner: catch-up push carries the current master
            late = start_fleet(["--devices", "1", "--devices-file", late_csv.name],
                               late_log)
            wire = await sniffer.collect(5.0)
            check("catch-up push carries master to the late joiner",
                  sent(wire, f"/{LATE_ID}/os/master", 0.5),
                  f"late traffic={[m for m in wire if f'/{LATE_ID}/' in m[0]]}")
            check("catch-up still pushes the stored params",
                  any(m[0] == f"/{LATE_ID}/p/gain" for m in wire),
                  f"late traffic={[m for m in wire if f'/{LATE_ID}/' in m[0]]}")

        check("late sim logged os/master delivery",
              "os/master 0.5" in read_log(late_log), read_log(late_log)[-300:])
        fleet_text = read_log(fleet_log)
        check("both fleet devices logged the master broadcast",
              all(f"sim{n} id={n} os/master 0.5" in fleet_text for n in (1, 2)),
              fleet_text[-400:])
    finally:
        for process in (server, fleet, late):
            if process is not None and process.poll() is None:
                process.terminate()
        for process in (server, fleet, late):
            if process is not None:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        sniffer.sock.close()

    log_text = read_log(server_log)
    check("server logged no traceback", "Traceback" not in log_text, log_text[-400:])
    for path in (fleet_log.name, late_log.name, server_log.name,
                 state_file, late_csv.name):
        try:
            os.unlink(path)
        except OSError:
            pass

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("seam-2 master-term checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
