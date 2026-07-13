#!/usr/bin/env python3
"""Focused browser-free verification for dist-2 node distribution."""

import heapq
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import types
import urllib.parse

sys.dont_write_bytecode = True


def repo_root():
    path = os.path.realpath(os.path.dirname(__file__))
    while path != os.path.dirname(path):
        if os.path.isfile(os.path.join(path, "tools", "simfleet.py")):
            return path
        path = os.path.dirname(path)
    raise RuntimeError("repository root not found")


ROOT = repo_root()
sys.path[:0] = [os.path.join(ROOT, "python"), os.path.join(ROOT, "python", "io"),
                os.path.join(ROOT, "tools")]

import pyOSC3  # noqa: E402


class FakeServer:
    def __init__(self, _target):
        self.handlers = {}

    def addMsgHandler(self, address, callback):
        self.handlers[address] = callback

    def close(self):
        pass


class FakeClient:
    def connect(self, _target):
        pass

    def send(self, _message):
        pass


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
sys.argv = ["bopos.py", "unknown"]

import bopos  # noqa: E402
import fetcher  # noqa: E402
import manifest  # noqa: E402
import simfleet  # noqa: E402
from pythonosc import osc_message, osc_message_builder  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def write_patch(path, engine="test", entrypoint="main.bin"):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, entrypoint), "w") as target:
        target.write("payload")
    with open(os.path.join(path, manifest.MANIFEST_NAME), "w") as target:
        json.dump({"engine": engine, "entrypoint": entrypoint,
                   "params": [], "caps": [], "slots": []}, target)


class ReplySocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))


with tempfile.TemporaryDirectory() as root:
    assets = os.path.join(root, "assets")
    patches = os.path.join(root, "patches")
    source = os.path.join(root, "source")
    os.makedirs(source)
    with open(os.path.join(source, "one.txt"), "w") as target:
        target.write("one")
    with open(os.path.join(source, manifest.MANIFEST_NAME), "w") as target:
        json.dump({"engine": "test", "entrypoint": "one.txt", "params": [],
                   "caps": [], "slots": []}, target)
    uri = "file:" + urllib.parse.quote(source)

    target_patch = os.path.join(patches, "mirror")
    os.makedirs(target_patch)
    with open(os.path.join(target_patch, "stale.txt"), "w") as target:
        target.write("stale")
    ok, detail = fetcher.fetch(uri, "patch:mirror", assets, patches)
    check("real patch fetch converges and prunes", ok
          and os.path.isfile(os.path.join(target_patch, "one.txt"))
          and not os.path.exists(os.path.join(target_patch, "stale.txt")), detail)

    os.makedirs(os.path.join(target_patch, ".git"))
    with open(os.path.join(source, "two.txt"), "w") as target:
        target.write("two")
    ok, detail = fetcher.fetch(uri, "patch:mirror", assets, patches)
    check("real patch fetch refuses git target", not ok
          and not os.path.exists(os.path.join(target_patch, "two.txt")), detail)
    check("gdrive scheme removed", not fetcher.fetch(
        "gdrive:https://example.invalid", "samplepacks", assets, patches)[0])
    check("unsafe patch name refused", not fetcher.fetch(
        uri, "patch:../escape", assets, patches)[0])
    check("ordinary asset fetch retained", fetcher.fetch(uri, "pack", assets, patches)[0]
          and os.path.isfile(os.path.join(assets, "pack", "one.txt")))

    samplepacks = os.path.join(assets, "samplepacks")
    os.makedirs(samplepacks)
    with open(os.path.join(samplepacks, "keep.wav"), "w") as target:
        target.write("asset")
    legacy_link_patch = os.path.join(patches, "legacy-link")
    write_patch(legacy_link_patch)
    os.makedirs(os.path.join(legacy_link_patch, "bop"))
    os.symlink(samplepacks, os.path.join(legacy_link_patch, "bop", "samplepacks"))
    ok, detail = fetcher.fetch(uri, "patch:legacy-link", assets, patches)
    check("framework legacy samplepacks link permits safe refetch", ok
          and os.path.isfile(os.path.join(samplepacks, "keep.wav"))
          and not os.path.lexists(os.path.join(
              legacy_link_patch, "bop", "samplepacks")), detail)

    outside = os.path.join(root, "outside")
    os.makedirs(outside)
    os.makedirs(os.path.join(source, "nested"))
    with open(os.path.join(source, "nested", "owned.txt"), "w") as target:
        target.write("owned")
    patch_escape = os.path.join(patches, "escape")
    os.makedirs(patch_escape)
    os.symlink(outside, os.path.join(patch_escape, "nested"))
    check("patch fetch rejects nested destination symlink", not fetcher.fetch(
        uri, "patch:escape", assets, patches)[0]
          and not os.path.exists(os.path.join(outside, "owned.txt")))
    asset_escape = os.path.join(assets, "unsafe")
    os.makedirs(asset_escape)
    os.symlink(outside, os.path.join(asset_escape, "nested"))
    check("asset fetch rejects nested destination symlink", not fetcher.fetch(
        uri, "unsafe", assets, patches)[0]
          and not os.path.exists(os.path.join(outside, "owned.txt")))

    preserved = os.path.join(patches, "preserved")
    write_patch(preserved)
    invalid_source = os.path.join(root, "invalid-source")
    os.makedirs(invalid_source)
    with open(os.path.join(invalid_source, "payload"), "w") as target:
        target.write("invalid")
    invalid_uri = "file:" + urllib.parse.quote(invalid_source)
    check("invalid fetched patch leaves prior patch atomically intact", not fetcher.fetch(
        invalid_uri, "patch:preserved", assets, patches)[0]
          and manifest.load(preserved)[0] is not None
          and os.path.isfile(os.path.join(preserved, "main.bin")))

    cli = [sys.executable, os.path.join(ROOT, "python", "manifest.py")]
    legacy = os.path.join(root, "legacy")
    os.makedirs(legacy)
    with open(os.path.join(legacy, "main.pd"), "w") as target:
        target.write("legacy")
    result = subprocess.run(cli + [legacy], text=True, capture_output=True)
    check("manifest-less main.pd fails loudly", result.returncode == 1
          and not result.stdout and "no bopos.patch.json" in result.stderr,
          repr((result.returncode, result.stdout, result.stderr)))

    valid = os.path.join(patches, "live")
    old = os.path.join(patches, "old")
    git_patch = os.path.join(patches, "gitpatch")
    write_patch(valid)
    write_patch(old)
    write_patch(git_patch)
    os.makedirs(os.path.join(git_patch, ".git"))
    os.makedirs(os.path.join(assets, "dropme"))
    with open(os.path.join(patches, "active_patch.txt"), "w") as target:
        target.write("live\n")

    old_bopos_dir = bopos.BOPOS_DIR
    old_active = bopos.active_patch_path
    old_run_command = bopos.run_command
    old_fetch = bopos.fetcher.fetch
    old_engine_alive = bopos.engine_alive
    bopos.BOPOS_DIR = root
    bopos.active_patch_path = lambda: os.path.join(root, "patches", open(
        os.path.join(root, "patches", "active_patch.txt")).read().strip())

    listing = bopos.installed_patches()
    by_name = {item["name"]: item for item in listing}
    check("real patch listing shape", {"gitpatch", "live", "mirror", "old"} <= set(by_name)
          and by_name["live"]["active"] and by_name["gitpatch"]["git"]
          and by_name["old"]["manifest"], repr(listing))

    bopos.drop_patch_callback(args=["live"])
    check("droppatch refuses active", os.path.isdir(valid))
    bopos.drop_patch_callback(args=["old"])
    check("droppatch removes inactive", not os.path.exists(old))
    bopos.drop_assets_callback(args=["dropme"])
    check("dropassets removes slot", not os.path.exists(os.path.join(assets, "dropme")))

    before = open(os.path.join(patches, "active_patch.txt")).read()
    bopos.switch_patch_callback(args=["legacy"])
    check("patch switch rejects no-manifest fallback",
          open(os.path.join(patches, "active_patch.txt")).read() == before)
    bopos.switch_patch_callback(args=["../escape"])
    check("patch switch rejects traversal",
          open(os.path.join(patches, "active_patch.txt")).read() == before)

    lifecycle = []
    run_marker = os.path.join(root, "run-id")

    def fake_run(argv, wait_for_start=False):
        lifecycle.append(os.path.basename(argv[1]))
        if os.path.basename(argv[1]) == "start-engine.sh":
            with open(run_marker, "w") as target:
                target.write(str(time.monotonic_ns()))
        return 0

    bopos.run_command = fake_run
    bopos.engine_alive = lambda: 1
    bopos.fetcher.fetch = lambda *_args: (True, "test fetch")
    reply = ReplySocket()
    bopos.queue_fetch("file:/source", "patch:live", "10.0.0.8", reply)
    deadline = time.time() + 3
    while not any(call[0][0] == "/os/fetched" for call in reply.calls) and time.time() < deadline:
        time.sleep(0.01)
    addresses = [(call[0][0], call[0][2:]) for call in reply.calls]
    check("active patch reports honest progress", addresses[:2] == [
        ("/os/fetch-progress", ["patch:live", "queued"]),
        ("/os/fetch-progress", ["patch:live", "fetching"])], repr(addresses))
    check("active patch stops then restarts before terminal", lifecycle == [
        "stop-engine.sh", "start-engine.sh"] and os.path.isfile(run_marker)
          and addresses[-1] == ("/os/fetched", ["patch:live", "ok"]),
          repr((lifecycle, addresses)))

    started = threading.Event()
    release = threading.Event()

    def slow_fetch(*_args):
        started.set()
        release.wait(2)
        return True, "coalesced"

    bopos.fetcher.fetch = slow_fetch
    first_reply = ReplySocket()
    second_reply = ReplySocket()
    bopos.queue_fetch("file:/coalesced", "patch:live", "10.0.0.8", first_reply)
    check("coalesced fetch enters worker", started.wait(1))
    bopos.queue_fetch("file:/coalesced", "patch:live", "10.0.0.9", second_reply)
    check("late coalesced requester sees current phase",
          second_reply.calls[0][0][2:] == ["patch:live", "fetching"],
          repr(second_reply.calls))
    release.set()
    deadline = time.time() + 3
    while (not any(call[0][0] == "/os/fetched" for call in second_reply.calls)
           and time.time() < deadline):
        time.sleep(0.01)
    check("coalesced requesters both receive terminal", any(
        call[0][0] == "/os/fetched" for call in first_reply.calls) and any(
        call[0][0] == "/os/fetched" for call in second_reply.calls))

    fetch_calls = []

    def fail_stop(argv, wait_for_start=False):
        lifecycle.append(os.path.basename(argv[1]))
        return 1 if os.path.basename(argv[1]) == "stop-engine.sh" else 0

    bopos.run_command = fail_stop
    bopos.fetcher.fetch = lambda *_args: fetch_calls.append(_args) or (True, "unexpected")
    lifecycle[:] = []
    reply = ReplySocket()
    bopos.queue_fetch("file:/stop-fail", "patch:live", "10.0.0.8", reply)
    deadline = time.time() + 3
    while not any(call[0][0] == "/os/fetched" for call in reply.calls) and time.time() < deadline:
        time.sleep(0.01)
    check("failed active stop aborts convergence", lifecycle == ["stop-engine.sh"]
          and not fetch_calls and reply.calls[-1][0][2:] == ["patch:live", "err"],
          repr((lifecycle, fetch_calls, reply.calls)))

    def fail_start(argv, wait_for_start=False):
        lifecycle.append(os.path.basename(argv[1]))
        return 1 if os.path.basename(argv[1]) == "start-engine.sh" else 0

    bopos.run_command = fail_start
    bopos.fetcher.fetch = lambda *_args: (True, "fetched")
    lifecycle[:] = []
    reply = ReplySocket()
    bopos.queue_fetch("file:/start-fail", "patch:live", "10.0.0.8", reply)
    deadline = time.time() + 3
    while not any(call[0][0] == "/os/fetched" for call in reply.calls) and time.time() < deadline:
        time.sleep(0.01)
    check("failed active restart makes terminal err", lifecycle == [
        "stop-engine.sh", "start-engine.sh"]
          and reply.calls[-1][0][2:] == ["patch:live", "err"],
          repr((lifecycle, reply.calls)))

    with open(os.path.join(patches, "active_patch.txt"), "w") as target:
        target.write("gitpatch\n")
    lifecycle[:] = []
    reply = ReplySocket()
    bopos.queue_fetch("file:/source", "patch:gitpatch", "10.0.0.8", reply)
    deadline = time.time() + 3
    while not any(call[0][0] == "/os/fetched" for call in reply.calls) and time.time() < deadline:
        time.sleep(0.01)
    check("active git patch refuses without engine disruption", not lifecycle
          and reply.calls[-1][0][2:] == ["patch:gitpatch", "err"], repr(reply.calls))

    class State:
        uid = "node-uid"
        id = 5
        version = "abc1234"
        update_model = "persistent"
        config = {"AUDIO_CHANNELS": "2"}

    request = pyOSC3.OSCMessage("/5/os/report")
    reply = ReplySocket()
    check("real report handled", bopos.handle_lan_datagram(
        request.getBinary(), ("10.0.0.9", 4000), reply, State()))
    report = json.loads(reply.calls[-1][0][2])
    check("real report includes hostname and v1.3", report["hostname"]
          and report["contract_version"] == "1.3", repr(report))
    check("removed real verbs absent", "update" not in bopos.PROVISION_VERBS
          and "getsamples" not in bopos.PROVISION_VERBS
          and {"updatebopos", "droppatch", "dropassets"} <= set(bopos.PROVISION_VERBS))

    os.makedirs(os.path.join(assets, "wire-drop"))
    drop = pyOSC3.OSCMessage("/5/os/dropassets")
    drop.append("wire-drop", "s")
    reply = ReplySocket()
    check("drop verb handled on real wire", bopos.handle_lan_datagram(
        drop.getBinary(), ("10.0.0.9", 4000), reply, State()) is True)
    deadline = time.time() + 3
    while not reply.calls and time.time() < deadline:
        time.sleep(0.01)
    check("real provisioning drop replies rev", reply.calls
          and reply.calls[-1][0][0] == "/os/rev", repr(reply.calls))

    bopos.BOPOS_DIR = old_bopos_dir
    bopos.active_patch_path = old_active
    bopos.run_command = old_run_command
    bopos.fetcher.fetch = old_fetch
    bopos.engine_alive = old_engine_alive


class SimSocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        message = osc_message.OscMessage(data)
        self.calls.append((message.address, list(message.params), target))

    def setsockopt(self, *_args):
        pass

    def bind(self, _target):
        pass

    def setblocking(self, _value):
        pass

    def close(self):
        pass


args = types.SimpleNamespace(protocol="v1", cmd_port=0, target="127.0.0.1",
                             report_port=5550, drop=0.0, jitter_ms=0.0,
                             state_dir=None, hb_interval=10.0, boot_secs=1.0,
                             sync_skew_ms=0.0, sync_jitter_ms=0.0)
device = simfleet.Device("02:00:00:00:00:05", "sim5", 5, "abc1234")
device.state = "running"
old_socket = simfleet.socket.socket
simfleet.socket.socket = lambda *_args: SimSocket()
fleet = simfleet.SimFleet(args, [device])
simfleet.socket.socket = old_socket


def sim_request(address, values=()):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value in values:
        builder.add_arg(value)
    before = len(fleet.sock.calls)
    fleet.receive_contract(builder.build().dgram, ("10.0.0.8", 4000))
    return fleet.sock.calls[before:]


calls = sim_request("/5/os/fetch", ("file:/source", "patch:newpatch"))
while fleet.events:
    _when, _sequence, callback, values = heapq.heappop(fleet.events)
    callback(*values)
new_calls = fleet.sock.calls[-3:]
check("sim patch fetch progress and terminal", [call[0] for call in new_calls] == [
    "/os/fetch-progress", "/os/fetch-progress", "/os/fetched"]
      and new_calls[-1][1] == ["patch:newpatch", "ok"], repr(new_calls))
calls = sim_request("/5/os/patches")
patches = json.loads(calls[-1][1][0])
check("sim patches lists fetched member", any(item["name"] == "newpatch"
                                                and not item["git"] for item in patches),
      repr(patches))

before = len(fleet.sock.calls)
sim_request("/5/os/fetch", ("file:/active", "patch:default"))
_when, _sequence, callback, values = heapq.heappop(fleet.events)
callback(*values)
check("sim active engine stops while fetching", device.engine_alive() == 0)
late = sim_request("/5/os/fetch", ("file:/active", "patch:default"))
check("sim coalesced requester sees fetching", late[-1][0] == "/os/fetch-progress"
      and late[-1][1] == ["patch:default", "fetching"], repr(late))
while fleet.events:
    _when, _sequence, callback, values = heapq.heappop(fleet.events)
    callback(*values)
terminal = [call for call in fleet.sock.calls[before:] if call[0] == "/os/fetched"]
check("sim restarts before coalesced terminals", device.engine_alive() == 1
      and len(terminal) == 2, repr(terminal))

before = len(fleet.sock.calls)
sim_request("/5/os/fetch", ("file:/serial-one", "patch:default"))
sim_request("/5/os/fetch", ("file:/serial-two", "patch:default"))
while fleet.events:
    _when, _sequence, callback, values = heapq.heappop(fleet.events)
    callback(*values)
serial = [call[0] for call in fleet.sock.calls[before:]
          if call[0] in ("/os/fetch-progress", "/os/fetched")]
check("sim serializes distinct fetch jobs per device", serial == [
    "/os/fetch-progress", "/os/fetch-progress", "/os/fetch-progress",
    "/os/fetched", "/os/fetch-progress", "/os/fetched"], repr(serial))
device.patches["gitpatch"] = {"git": True, "manifest": True}
calls = sim_request("/5/os/fetch", ("file:/source", "patch:gitpatch"))
check("sim refuses git patch", calls[-1][0] == "/os/fetched"
      and calls[-1][1] == ["patch:gitpatch", "err"], repr(calls))
before = len(fleet.sock.calls)
sim_request("/5/os/update")
sim_request("/5/os/getsamples")
check("sim removed verbs produce no reply", len(fleet.sock.calls) == before)
sim_request("/5/os/updatebopos")
check("sim updatebopos spelling accepted", device.state == "updating")
fleet.events[:] = []
device.state = "running"
sim_request("/5/os/report")
report = json.loads(fleet.sock.calls[-1][1][0])
check("sim report includes hostname and v1.3", report["hostname"] == "sim5"
      and report["contract_version"] == "1.3", repr(report))
sim_request("/5/os/droppatch", ("newpatch",))
check("sim droppatch removes inactive and replies", "newpatch" not in device.patches
      and fleet.sock.calls[-1][0] == "/os/rev")

print()
if FAILURES:
    print("{} FAILURE(S): {}".format(len(FAILURES), FAILURES))
    raise SystemExit(1)
print("all checks passed")
