#!/usr/bin/env python3
"""Checks for the os-admin-verbs stitch.

Part 1 exercises helper.py's LAN dispatch directly with monkeypatched
callbacks (nothing reboots the box running the test). Part 2 runs the real
dashboard against a real simfleet and drives the "update all and watch them
come back" story over the websocket.

Run with the stitch venv: python needs pyOSC3, python-osc, websockets and
the dashboard requirements on PYTHONPATH/installed.
"""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

# locate the repo by marker, not by depth — the loom moves this file
# from threads/<t>/<stitch>.stitching/ to tied/<stitch>/ when tied
REPO = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "python"))

FAILURES = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print("[{}] {}{}".format(status, label, " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


# ---------------------------------------------------------------- part 1
import pyOSC3


class FakeServer:
    def __init__(self, target):
        self.handlers = {}

    def addMsgHandler(self, address, callback):
        self.handlers[address] = callback

    def close(self):
        pass


class FakeClient:
    def connect(self, target):
        pass

    def send(self, message):
        pass


class ReplySocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))

    def wait(self, count=1, timeout=3.0):
        end = time.monotonic() + timeout
        while len(self.calls) < count and time.monotonic() < end:
            time.sleep(0.02)
        return self.calls


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
sys.argv = ["helper.py", "unknown"]
import helper


def datagram(address, *args):
    msg = pyOSC3.OSCMessage(address)
    for value in args:
        msg.append(value)
    return msg.getBinary()


class Recorder:
    """Stands in for a 7770 callback; optionally flips the resolved sha."""

    def __init__(self, name, new_sha=None):
        self.name = name
        self.new_sha = new_sha
        self.calls = []
        self.done = threading.Event()

    def __call__(self, path='', tags='', args='', source=''):
        self.calls.append(list(args))
        if self.new_sha is not None:
            helper.resolve_version = lambda: self.new_sha
        self.done.set()


def part1():
    state = helper.node_state
    state.id = 3
    state.uid = "aa:bb:cc:dd:ee:ff"
    state.update_model = "persistent"
    saved_resolve = helper.resolve_version
    helper.resolve_version = lambda: "0000aaa"

    # provisioning verb: callback runs, receipt follows with the post-pull sha
    recorder = Recorder("update", new_sha="0000aab")
    helper.PROVISION_VERBS["update"] = recorder
    sock = ReplySocket()
    handled = helper.handle_lan_datagram(datagram("/3/os/update"), ("10.0.0.9", 4242), sock, state)
    check("update: dispatched", handled)
    check("update: callback ran", recorder.done.wait(3.0))
    calls = sock.wait(1)
    check("update: one receipt", len(calls) == 1, repr(calls))
    if calls:
        decoded, target = calls[0]
        check("update: /os/rev shape",
              decoded[0] == "/os/rev" and decoded[2:] == ["0000aab", "persistent", state.uid],
              repr(decoded))
        check("update: unicast to requester:5550", target == ("10.0.0.9", 5550), repr(target))

    # selector must match: another id's verb is ignored
    other = ReplySocket()
    recorder2 = Recorder("update")
    helper.PROVISION_VERBS["update"] = recorder2
    handled = helper.handle_lan_datagram(datagram("/4/os/update"), ("10.0.0.9", 4242), other, state)
    check("update: wrong selector ignored", not handled and not other.calls)

    # provisioning verb with args: strings reach the callback
    helper.resolve_version = lambda: "0000aab"
    recorder = Recorder("checkout", new_sha="0000aac")
    helper.PROVISION_VERBS["checkout"] = recorder
    sock = ReplySocket()
    helper.handle_lan_datagram(datagram("/all/os/checkout", "dev"), ("10.0.0.9", 4242), sock, state)
    check("checkout: callback ran", recorder.done.wait(3.0))
    check("checkout: branch arg passed", recorder.calls and recorder.calls[0] == ["dev"],
          repr(recorder.calls))
    calls = sock.wait(1)
    check("checkout: bumped sha in receipt", calls and calls[0][0][2] == "0000aac", repr(calls))

    # lifecycle verb: receipt precedes execution
    order = []
    recorder = Recorder("reboot")
    original_call = recorder.__call__

    def reboot_callback(path='', tags='', args='', source=''):
        order.append("exec")
        recorder.done.set()

    helper.LIFECYCLE_VERBS["reboot"] = reboot_callback

    class OrderedSocket(ReplySocket):
        def sendto(self, data, target):
            order.append("reply")
            super().sendto(data, target)

    sock = OrderedSocket()
    helper.resolve_version = lambda: "0000aac"
    handled = helper.handle_lan_datagram(datagram("/3/os/reboot"), ("10.0.0.9", 4242), sock, state)
    check("reboot: dispatched", handled)
    check("reboot: executed", recorder.done.wait(3.0))
    check("reboot: reply before execution", order and order[0] == "reply", repr(order))

    # restart-engine is a lifecycle verb too
    recorder = Recorder("restart-engine")
    helper.LIFECYCLE_VERBS["restart-engine"] = recorder
    sock = ReplySocket()
    handled = helper.handle_lan_datagram(datagram("/3/os/restart-engine"), ("10.0.0.9", 4242),
                                         sock, state)
    check("restart-engine: dispatched", handled)
    check("restart-engine: executed", recorder.done.wait(3.0))
    check("restart-engine: receipt sent", bool(sock.wait(1)))

    # ephemeral: provisioning no-ops but the receipt still goes out;
    # lifecycle still executes
    state.update_model = "ephemeral"
    recorder = Recorder("update")
    helper.PROVISION_VERBS["update"] = recorder
    sock = ReplySocket()
    helper.handle_lan_datagram(datagram("/3/os/update"), ("10.0.0.9", 4242), sock, state)
    calls = sock.wait(1)
    check("ephemeral update: receipt sent", bool(calls))
    if calls:
        check("ephemeral update: model in receipt", calls[0][0][3] == "ephemeral", repr(calls))
    time.sleep(0.3)
    check("ephemeral update: callback NOT run", not recorder.calls, repr(recorder.calls))

    recorder = Recorder("shutdown")
    helper.LIFECYCLE_VERBS["shutdown"] = recorder
    sock = ReplySocket()
    helper.handle_lan_datagram(datagram("/3/os/shutdown"), ("10.0.0.9", 4242), sock, state)
    check("ephemeral shutdown: still executes", recorder.done.wait(3.0))

    state.update_model = "persistent"
    helper.resolve_version = saved_resolve


# ---------------------------------------------------------------- part 2
import websockets


async def wait_message(ws, wanted, timeout=8):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        message = json.loads(await asyncio.wait_for(ws.recv(), end - time.monotonic()))
        if message.get("type") == wanted:
            return message
    raise asyncio.TimeoutError(wanted)


async def part2():
    with tempfile.TemporaryDirectory() as temp:
        state_file = os.path.join(temp, "installation.json")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"), "--port", "18081",
            "--listen-port", "15551", "--send-port", "16661", "--osc-target", "127.0.0.1",
            "--state-file", state_file,
        ], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        # 4 devices: sim4 ephemeral, sim3 engine-dead (helper still answers)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "4",
            "--engine-dead", "2", "--ephemeral", "1", "--target", "127.0.0.1",
            "--report-port", "15551", "--cmd-port", "16661", "--hb-interval", "1.0",
        ], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            ws = None
            for _ in range(50):
                try:
                    ws = await websockets.connect("ws://127.0.0.1:18081/ws")
                    break
                except OSError:
                    await asyncio.sleep(0.2)
            check("e2e: websocket connected", ws is not None)
            if ws is None:
                return

            # wait until all four devices heartbeat in
            devices = {}
            end = time.monotonic() + 10
            while len(devices) < 4 and time.monotonic() < end:
                message = json.loads(await asyncio.wait_for(ws.recv(), end - time.monotonic()))
                if message.get("type") in ("device_update", "rev"):
                    device = message["data"]
                    devices[device["uid"]] = device
            check("e2e: 4 devices online", len(devices) == 4, repr(sorted(devices)))
            start_sha = "a1b2c3d"

            # the verify criterion: update all, every device answers /os/rev
            await ws.send(json.dumps({"type": "action", "data": {"uid": "all", "verb": "update"}}))
            revs = {}
            end = time.monotonic() + 10
            while len(revs) < 4 and time.monotonic() < end:
                try:
                    message = json.loads(await asyncio.wait_for(ws.recv(), end - time.monotonic()))
                except asyncio.TimeoutError:
                    break
                if message.get("type") == "rev":
                    device = message["data"]
                    revs[device["uid"]] = device["rev"]
            check("e2e: every device replied /os/rev", len(revs) == 4, repr(sorted(revs)))
            bumped = "a1b2c3e"
            persistent = {uid: rev for uid, rev in revs.items() if rev["model"] == "persistent"}
            ephemeral = {uid: rev for uid, rev in revs.items() if rev["model"] == "ephemeral"}
            check("e2e: one ephemeral device", len(ephemeral) == 1, repr(revs))
            check("e2e: persistent devices report the bumped sha",
                  persistent and all(rev["sha"] == bumped for rev in persistent.values()),
                  repr(revs))
            check("e2e: ephemeral device honestly reports the old sha",
                  all(rev["sha"] == start_sha for rev in ephemeral.values()), repr(revs))
            engine_dead = [uid for uid, device in devices.items()
                           if not device.get("engine_alive")]
            check("e2e: dead-engine device still answered",
                  engine_dead and all(uid in revs for uid in engine_dead),
                  "dead={} revs={}".format(engine_dead, sorted(revs)))
            await ws.close()
        finally:
            fleet.terminate()
            server.terminate()
            fleet.wait(timeout=5)
            server.wait(timeout=5)


def main():
    print("--- part 1: helper.py LAN dispatch (fakes; nothing executes for real)")
    part1()
    print("--- part 2: dashboard + simfleet end to end")
    asyncio.run(part2())
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
