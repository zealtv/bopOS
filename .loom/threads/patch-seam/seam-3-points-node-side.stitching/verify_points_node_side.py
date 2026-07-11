#!/usr/bin/env python3
"""Verification for seam-3: node-side point decomposition (contract sec 4.1).

Two parts, browser- and hardware-free:

  A. the REAL python/helper.py, imported in-process (binds 7770 harmlessly,
     sync-2 style): a true-N /os/assign lands element positions, then /pt
     frame / sparse / clear datagrams through handle_lan_datagram produce
     shaped scalars `/pt <pointId> <element> <v>` on the engine socket (6661)
     -- per point, per element, 1-based element index, release-to-zero.

  B. the full stack: real dashboard/server.py (broadcast OSC target) + real
     simfleet + a SO_REUSEPORT sniffer on the sim command port. Asserts the
     wire shapes (one atomic frame for a static set -- silence = hold; ~25 Hz
     only while a point moves; 5-arg sparse; /pt/clear) and that every sim-
     logged proximity equals falloff(distance) recomputed from the sniffed
     geometry by the shared module (node-computed, never dashboard-computed).
     A late-joining sim with a persisted assignment gets the current frame
     via the params catch-up push (and master, seam-2 regression).

Deps (venv ~/.venvs/bopos): pip install fastapi uvicorn[standard] python-osc
websockets pyOSC3.  Run: ~/.venvs/bopos/bin/python verify_points_node_side.py
"""
import asyncio
import json
import math
import os
import re
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
sys.path.insert(0, os.path.join(REPO, "python"))

import pointfield  # noqa: E402

HTTP_PORT = 18094
REPORT_PORT = 15583
CMD_PORT = 16693
LATE_ID = 7
LATE_MAC = "02:53:49:4d:ff:01"

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


# --- part A: the real helper.py, loopback ---------------------------------

def helper_checks():
    from pyOSC3 import OSCMessage
    from store import Store

    engine = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    engine.bind(("127.0.0.1", 6661))
    engine.settimeout(1.0)

    import helper
    helper.set_hostname = lambda name: None      # no hostnamectl on a laptop
    helper.node_state.store = Store("/nonexistent", persistent=False)
    helper.node_state.uid = "verify-node"
    helper.node_state.id = 5
    helper.node_state.elements = []
    helper.node_state.points = {}
    reply = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def deliver(address, args):
        msg = OSCMessage(address)
        for value in args:
            msg.append(value)
        return helper.handle_lan_datagram(msg.getBinary(), ("127.0.0.1", 0), reply)

    def engine_messages(expected):
        received = []
        try:
            while len(received) < expected:
                message = osc_message.OscMessage(engine.recv(65535))
                received.append((message.address, list(message.params)))
        except socket.timeout:
            pass
        return received

    handled = deliver("/all/os/assign",
                      ["verify-node", 5, "verify-node", 2.0, 2.0, 6.0, 6.0])
    check("A: true-N assign lands element positions",
          handled and helper.node_state.elements == [[2.0, 2.0], [6.0, 6.0]],
          f"elements={helper.node_state.elements}")
    check("A: assignment persists element pairs",
          helper.resolve_elements(helper.node_state.store) == [[2.0, 2.0], [6.0, 6.0]])
    engine_messages(2)  # drain the assign's /id notification (and any noise)

    deliver("/pt", [1, 1, 2.0, 2.0, 3.0, 0])   # frame: one linear point at el1
    got = engine_messages(2)
    check("A: frame decomposes per element, 1-based, on 6661",
          got == [("/pt", [1, 1, 1.0]), ("/pt", [1, 2, 0.0])], f"got={got}")

    deliver("/pt", [2, 6.0, 6.0, 2.0, 1])      # sparse upsert at element 2
    got = engine_messages(2)
    check("A: sparse upsert recomputes only that point",
          got == [("/pt", [2, 1, 0.0]), ("/pt", [2, 2, 1.0])], f"got={got}")

    deliver("/pt/clear", [2])
    got = engine_messages(2)
    check("A: clear releases the point to zero once",
          got == [("/pt", [2, 1, 0.0]), ("/pt", [2, 2, 0.0])], f"got={got}")

    deliver("/pt", [0])                        # empty frame: full-state removal
    got = engine_messages(2)
    check("A: empty frame releases the remaining point",
          got == [("/pt", [1, 1, 0.0]), ("/pt", [1, 2, 0.0])], f"got={got}")
    engine.close()
    reply.close()


# --- part B: full stack over the wire --------------------------------------

class Sniffer:
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


def logged_values(text, hostname, point_id, element):
    """The v= values a sim device logged for one point x element, in order."""
    pattern = re.compile(rf"\s{hostname} id=\S+ pt {point_id} el{element} v=([\d.]+)")
    return [match.group(1) for match in pattern.finditer(text)]


def expected_for(frames, point_id, position):
    """%.6f falloff values recomputed from sniffed frame geometry."""
    values = []
    for address, args in frames:
        if address != "/pt":
            continue
        parsed = pointfield.parse_wire(["pt"], args)
        if not parsed or parsed[0] != "frame" or point_id not in parsed[1]:
            continue
        x, y, r, f = parsed[1][point_id]
        distance = math.hypot(position[0] - x, position[1] - y)
        values.append(f"{pointfield.falloff(f, distance, r):.6f}")
    return values


async def ws_send(ws, kind, data):
    await ws.send(json.dumps({"type": kind, "data": data}))


async def stack_checks():
    fleet_log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    late_log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    server_log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    state_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    late_csv = tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False)
    late_csv.write(f"mac,hostname,id\n{LATE_MAC},simlate,{LATE_ID}\n")
    late_csv.flush()
    late_state = tempfile.mkdtemp(prefix="simlate-state-")
    with open(os.path.join(late_state, LATE_MAC.replace(":", "-") + ".json"),
              "w") as target:  # a persisted assignment: id 7, one element at (2,2)
        json.dump({"id": LATE_ID, "name": "simlate", "positions": [2.0, 2.0]}, target)

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
        await asyncio.sleep(4)
        async with websockets.connect(f"ws://127.0.0.1:{HTTP_PORT}/ws") as ws:
            state = json.loads(await ws.recv())
            devices = state["data"]["devices"]
            uid1 = next(u for u, d in devices.items() if int(d["id"]) == 1)
            uid2 = next(u for u, d in devices.items() if int(d["id"]) == 2)

            # position the fleet: sim1 one element, sim2 two elements
            await ws_send(ws, "assign_device", {"uid": uid1, "id": 1, "name": "sim1"})
            await ws_send(ws, "assign_device", {"uid": uid2, "id": 2, "name": "sim2"})
            await ws_send(ws, "set_position", {"uid": uid1, "pos1": [2.0, 2.0]})
            await ws_send(ws, "set_position", {"uid": uid2, "pos1": [8.0, 6.0],
                                               "pos2": [4.0, 4.0]})
            await asyncio.sleep(0.8)
            assigns = [m for m in sniffer.drain() if m[0] == "/all/os/assign"]
            check("B: assign rides element pairs on the wire",
                  any(len(m[1]) == 7 and str(m[1][0]) == uid2 for m in assigns),
                  f"assigns={assigns}")

            # static set: one atomic frame, then silence (= hold)
            await ws_send(ws, "set_points", {"points": [
                {"id": 1, "x": 2.0, "y": 2.0, "r": 3.0, "falloff": "linear"}]})
            wire = await sniffer.collect(1.2)
            frames = [m for m in wire if m[0] == "/pt"]
            check("B: static set is exactly one frame",
                  len(frames) == 1 and frames[0][1][:2] == [1, 1],
                  f"frames={frames}")

            # moving point: ~25 Hz frames; sim values == falloff(sniffed geometry)
            await ws_send(ws, "set_points", {"points": [
                {"id": 2, "x": 5.0, "y": 4.0, "r": 4.0, "falloff": "gauss",
                 "motion": {"type": "orbit", "center": [5.0, 4.0],
                            "radius": 2.0, "period": 2.0}}]})
            moving = await sniffer.collect(1.0)
            await ws_send(ws, "set_points", {"points": [
                {"id": 1, "x": 2.0, "y": 2.0, "r": 3.0, "falloff": "linear"}]})
            await asyncio.sleep(0.6)
            moving += sniffer.drain()  # stragglers + the stopping static frame
            frame_count = len([m for m in moving if m[0] == "/pt"
                               and len(m[1]) > 5])
            check("B: moving point broadcasts ~25 Hz", 15 <= frame_count <= 45,
                  f"frames={frame_count}")
            expected = expected_for(moving, 2, (2.0, 2.0)) + ["0.000000"]
            got = logged_values(read_log(fleet_log), "sim1", 2, 1)
            check("B: sim proximity == falloff(distance) for every frame",
                  sorted(got) == sorted(expected) and len(set(got)) > 10,
                  f"got {len(got)} values ({len(set(got))} distinct), "
                  f"expected {len(expected)}")

            # sparse upsert: 5-arg wire form, only that point recomputed
            await ws_send(ws, "set_point", {"point": {
                "id": 3, "x": 4.0, "y": 4.0, "r": 2.0, "falloff": "smooth"}})
            wire = await sniffer.collect(0.8)
            sparse = [m for m in wire if m[0] == "/pt" and len(m[1]) == 5]
            check("B: sparse upsert is the 5-arg form",
                  len(sparse) == 1 and sparse[0][1][0] == 3, f"wire={wire}")
            text = read_log(fleet_log)
            check("B: sparse edit hits element 2 of sim2",
                  logged_values(text, "sim2", 3, 2) == ["1.000000"]
                  and logged_values(text, "sim2", 3, 1) == ["0.000000"],
                  f"sim2 pt3: el1={logged_values(text, 'sim2', 3, 1)} "
                  f"el2={logged_values(text, 'sim2', 3, 2)}")

            # clear: wire form + release to zero
            await ws_send(ws, "clear_point", {"id": 3})
            wire = await sniffer.collect(0.8)
            check("B: clear_point emits /pt/clear",
                  any(m[0] == "/pt/clear" and m[1] == [3] for m in wire),
                  f"wire={wire}")
            check("B: cleared point releases to zero",
                  logged_values(read_log(fleet_log), "sim2", 3, 2)[-1] == "0.000000")

            # late joiner with a persisted assignment: catch-up carries the
            # current frame (and master -- the seam-2 chain stays intact)
            sniffer.drain()
            late = start_fleet(["--devices", "1", "--devices-file", late_csv.name,
                                "--state-dir", late_state], late_log)
            wire = await sniffer.collect(5.0)
            check("B: catch-up re-broadcasts the frame for a late joiner",
                  any(m[0] == "/pt" and len(m[1]) > 5 for m in wire),
                  f"pt traffic={[m for m in wire if m[0].startswith('/pt')]}")
            check("B: catch-up still carries master",
                  any(m[0] == f"/{LATE_ID}/os/master" for m in wire),
                  f"late traffic={[m for m in wire if f'/{LATE_ID}/' in m[0]]}")
            check("B: late joiner decomposes from persisted elements",
                  logged_values(read_log(late_log), "simlate", 1, 1)[-1:] == ["1.000000"],
                  read_log(late_log)[-300:])
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
    check("B: server logged no traceback", "Traceback" not in log_text,
          log_text[-400:])
    for path in (fleet_log.name, late_log.name, server_log.name,
                 state_file, late_csv.name):
        try:
            os.unlink(path)
        except OSError:
            pass


async def main():
    helper_checks()
    await stack_checks()
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("seam-3 node-side point checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
