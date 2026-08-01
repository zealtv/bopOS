#!/usr/bin/env python3
"""Focused managed-simulation cue/point delivery and view-switch checks."""
import asyncio
import os
import socket
import sys
import tempfile
import time
from types import SimpleNamespace

from pythonosc import osc_message

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "audition.py")):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, "dashboard"))
from server import Dashboard  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}" +
          (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_udp_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def engine_pair():
    for base in range(36000, 50000, 2):
        sockets = []
        try:
            for port in (base, base + 1):
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(("127.0.0.1", port))
                sock.setblocking(False)
                sockets.append(sock)
            return base, sockets
        except OSError:
            for sock in sockets:
                sock.close()
    raise RuntimeError("no adjacent fake engine ports available")


async def receive(sock, address, timeout=2.0):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        try:
            data, _source = await asyncio.wait_for(loop.sock_recvfrom(sock, 65535),
                                                   deadline - loop.time())
        except asyncio.TimeoutError:
            break
        message = osc_message.OscMessage(data)
        if message.address == address:
            return list(message.params), time.monotonic()
    return None, None


async def drain(sock):
    while True:
        try:
            await asyncio.wait_for(asyncio.get_running_loop().sock_recvfrom(sock, 65535), .03)
        except asyncio.TimeoutError:
            return


async def main():
    engine_base, engines = engine_pair()
    with tempfile.TemporaryDirectory() as temp:
        args = SimpleNamespace(
            state_file=os.path.join(temp, "installation.json"), devices_file=None,
            listen_port=free_udp_port(), send_port=free_udp_port(),
            osc_target="127.0.0.1", assets_dir=os.path.join(temp, "assets"),
            patches_dir=os.path.join(temp, "patches"), port=0, public_url=None,
            sim_audio_backend="none", sim_no_engine=True,
            sim_engine_port_base=engine_base,
        )
        dashboard = Dashboard(args)
        await dashboard.start()
        try:
            for seat_id, position in ((0, [1, 1]), (1, [9, 1])):
                await dashboard.handle_ws({"type": "add_seat", "data": {
                    "id": seat_id, "name": f"seat-{seat_id}",
                    "positions": [position], "patch": "demo-pd", "params": {}}})
            await dashboard.handle_ws({"type": "set_simulation", "data": {"active": True}})
            deadline = time.monotonic() + 5
            while (time.monotonic() < deadline and
                   len([d for d in dashboard.state.devices.values() if d.get("virtual")]) < 2):
                await asyncio.sleep(.05)
            await asyncio.sleep(.3)
            for sock in engines:
                await drain(sock)

            await dashboard.handle_ws({"type": "set_point", "data": {"point": {
                "id": 7, "x": 1, "y": 1, "r": 10, "falloff": "linear"}}})
            point_messages = [await receive(sock, "/pt") for sock in engines]
            values = [message for message, _at in point_messages]
            check("managed simulation decomposes point geometry per virtual seat",
                  all(value and value[:2] == [7, 0] for value in values), repr(values))
            check("point values reflect each seat's authored position",
                  abs(values[0][2] - 1.0) < 1e-5 and abs(values[1][2] - .2) < 1e-5,
                  repr(values))

            await dashboard.handle_ws({"type": "clear_point", "data": {"id": 7}})
            cleared = [(await receive(sock, "/pt"))[0] for sock in engines]
            check("point clear releases every virtual engine element",
                  all(value == [7, 0, 0.0] for value in cleared), repr(cleared))

            for sock in engines:
                await drain(sock)
            started = time.monotonic()
            await dashboard.handle_ws({"type": "fire_cue", "data": {
                "cue_id": "start", "lead_ms": 250}})
            cue_messages = [await receive(sock, "/cue") for sock in engines]
            check("managed simulation fires bare cues into every virtual engine",
                  all(message == ["start"] for message, _at in cue_messages),
                  repr(cue_messages))
            times = [at for _message, at in cue_messages]
            check("cue honours leader deadline on the shared host clock",
                  all(at is not None and .20 <= at - started <= .60 for at in times),
                  repr([None if at is None else at - started for at in times]))
            check("virtual cue fan-out remains tightly grouped",
                  all(at is not None for at in times) and max(times) - min(times) < .02,
                  repr(times))
        finally:
            await dashboard.stop()
            for sock in engines:
                sock.close()

    technical = open(os.path.join(REPO, "dashboard/static/index.html"), encoding="utf-8").read()
    facilitator = open(os.path.join(REPO, "dashboard/static/facilitator.html"),
                       encoding="utf-8").read()
    check("Facilitator button precedes the technical bopOS wordmark",
          technical.index('id="facilitator-link"') < technical.index("<h1>bopOS</h1>"))
    check("Technical button precedes the facilitator bopOS wordmark",
          facilitator.index('id="technical-link"') < facilitator.index('id="venue-name"'))
    note = open(os.path.join(REPO, ".notes/dashboard-development-context.md"),
                encoding="utf-8").read()
    check("mixed-engine simulation remains explicitly deferred", "mixed-engine policy now" in note)
    print(f"\n{9-len(FAILURES)}/9 passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
