"""Direct checks for the patch-manifest stitching implementation.

Run with PYTHONPATH=<pylib>:python:python/io.
"""
import json
import os
import subprocess
import sys
import tempfile
import types

import pyOSC3

FAILURES = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print("[{}] {}{}".format(status, label, " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


class FakeServer:
    def __init__(self, target):
        self.handlers = {}

    def addMsgHandler(self, address, callback):
        self.handlers[address] = callback

    def close(self):
        pass


class FakeClient:
    def __init__(self):
        self.sent = []

    def connect(self, target):
        pass

    def send(self, message):
        self.sent.append(pyOSC3.decodeOSC(message.getBinary()))


class ReplySocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
sys.argv = ["helper.py", "unknown"]
import bopos as helper
import manifest

REPO = helper.BOPOS_DIR

# --- A. manifest loader and CLI ----------------------------------------------
default_patch = os.path.join(REPO, "patches", "demo-pd")
loaded, error = manifest.load(default_patch)
check("manifest.load valid default", loaded is not None and error is None)


def invalid_manifest(label, value, files=()):
    with tempfile.TemporaryDirectory() as root:
        for name in files:
            open(os.path.join(root, name), "w").close()
        with open(os.path.join(root, manifest.MANIFEST_NAME), "w") as target:
            json.dump(value, target)
        result, error = manifest.load(root)
        check(label, result is None and bool(error), repr(error))


base = {"engine": "pd", "entrypoint": "main.pd", "params": [], "caps": []}
invalid_manifest("missing entrypoint", base)
invalid_manifest("bad param name", dict(base, params=[{"name": "bad name", "type": "f"}]), ["main.pd"])
invalid_manifest("bad param type", dict(base, params=[{"name": "gain", "type": "x"}]), ["main.pd"])
invalid_manifest("min greater than max", dict(base, params=[{"name": "gain", "type": "f", "min": 2, "max": 1}]), ["main.pd"])
invalid_manifest("default out of range", dict(base, params=[{"name": "gain", "type": "f", "min": 0, "max": 1, "default": 2}]), ["main.pd"])
invalid_manifest("non-list caps", dict(base, caps="screen"), ["main.pd"])

cli = [sys.executable, os.path.join(REPO, "python", "manifest.py")]
result = subprocess.run(cli + [default_patch], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
scope = {}
exec(result.stdout, {}, scope)  # the lines must be eval-able assignments
check("manifest CLI valid", result.returncode == 0
      and scope == {"ENGINE": "pd", "ENTRYPOINT": "main.pd"}, result.stdout + result.stderr)
with tempfile.TemporaryDirectory() as root:
    open(os.path.join(root, "main.pd"), "w").close()
    result = subprocess.run(cli + [root], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    check("manifest CLI legacy exit 3", result.returncode == 3 and "ENGINE='pd'" in result.stdout
          and "ENTRYPOINT='main.pd'" in result.stdout, repr((result.returncode, result.stdout)))
    with open(os.path.join(root, manifest.MANIFEST_NAME), "w") as target:
        target.write("{")
    result = subprocess.run(cli + [root], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    check("manifest CLI broken exit 1 with fallback", result.returncode == 1
          and "ENGINE='pd'" in result.stdout and "ENTRYPOINT='main.pd'" in result.stdout,
          repr((result.returncode, result.stdout)))

# --- B. helper params and report ---------------------------------------------
class State:
    uid = "node-uid"
    id = 5
    version = "abc1234"
    update_model = "persistent"
    config = {"AUDIO_CHANNELS": "6"}


def request(member):
    msg = pyOSC3.OSCMessage("/5/os/" + member)
    reply = ReplySocket()
    handled = helper.handle_lan_datagram(msg.getBinary(), ("10.0.0.9", 40000), reply, State())
    return handled, reply.calls


old_active_patch_path = helper.active_patch_path
helper.active_patch_path = lambda: default_patch
handled, calls = request("params")
raw = manifest.raw(default_patch)
check("helper params verbatim unicast", handled and calls == [
    (["/os/params", ",s", raw], ("10.0.0.9", 5550))], repr(calls))
helper.active_patch_path = lambda: None
handled, calls = request("params")
check("helper params legal empty", handled and calls == [
    (["/os/params", ","], ("10.0.0.9", 5550))], repr(calls))
helper.active_patch_path = lambda: default_patch
handled, calls = request("report")
report = json.loads(calls[0][0][2])
check("helper report shape", handled and set(report) == {
    "uid", "engine", "has_i2c", "has_wifi", "audio_channels", "screen", "patch",
    "uptime", "git_rev", "update_model", "contract_version"}, repr(report))
check("helper report facts", report["uid"] == "node-uid" and report["git_rev"] == "abc1234"
      and report["update_model"] == "persistent" and report["contract_version"] == "1.0"
      and report["audio_channels"] == 6 and report["screen"] is False, repr(report))
helper.active_patch_path = old_active_patch_path

# --- C. patch validation and engine liveness ---------------------------------
old_bopos = helper.BOPOS_DIR
old_system = helper.os.system
old_run = helper.subprocess.run
with tempfile.TemporaryDirectory() as root:
    helper.BOPOS_DIR = root
    patches = os.path.join(root, "patches")
    os.makedirs(patches)
    outcomes = []
    helper.os.system = lambda command: outcomes.append(command) or 0
    helper.subprocess.run = lambda *args, **kwargs: types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
    valid = os.path.join(patches, "valid")
    os.makedirs(valid)
    open(os.path.join(valid, "app.bin"), "w").close()
    with open(os.path.join(valid, manifest.MANIFEST_NAME), "w") as target:
        json.dump({"engine": "app", "entrypoint": "app.bin"}, target)
    helper.switch_patch_callback(args=["valid"])
    check("patch accepts manifest-only", open(os.path.join(patches, "active_patch.txt")).read().strip() == "valid")
    legacy = os.path.join(patches, "legacy")
    os.makedirs(legacy)
    open(os.path.join(legacy, "main.pd"), "w").close()
    helper.switch_patch_callback(args=["legacy"])
    check("patch accepts main.pd-only", open(os.path.join(patches, "active_patch.txt")).read().strip() == "legacy")
    empty = os.path.join(patches, "empty")
    os.makedirs(empty)
    before = open(os.path.join(patches, "active_patch.txt")).read()
    helper.switch_patch_callback(args=["empty"])
    check("patch rejects neither", open(os.path.join(patches, "active_patch.txt")).read() == before)

    run = os.path.join(root, "run")
    proc = os.path.join(root, "proc")
    os.makedirs(run)
    os.makedirs(os.path.join(proc, str(os.getpid())))
    with open(os.path.join(run, "engine.name"), "w") as target:
        target.write("test-engine\n")
    with open(os.path.join(run, "engine.pid"), "w") as target:
        target.write(str(os.getpid()))
    with open(os.path.join(proc, str(os.getpid()), "comm"), "w") as target:
        target.write("test-engine\n")
    old_proc = helper.PROC_DIR
    helper.PROC_DIR = proc
    check("engine_alive uses engine pid/name", helper.engine_alive() == 1)
    helper.PROC_DIR = old_proc
helper.BOPOS_DIR = old_bopos
helper.os.system = old_system
helper.subprocess.run = old_run

# --- D. simfleet contract -----------------------------------------------------
sys.path.insert(0, os.path.join(REPO, "tools"))
import simfleet
from pythonosc import osc_message, osc_message_builder

args = types.SimpleNamespace(protocol="v1", cmd_port=0, target="127.0.0.1", report_port=5550,
                             drop=0.0, jitter_ms=0.0, legacy_reports=False, state_dir=None,
                             hb_interval=10.0, boot_secs=1.0)
device = simfleet.Device("02:00:00:00:00:05", "sim5", 5, "abc1234")
device.state = "running"


class SimSocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        message = osc_message.OscMessage(data)
        self.calls.append((message.address, list(message.params), target))

    def setsockopt(self, *args):
        pass

    def bind(self, target):
        pass

    def setblocking(self, value):
        pass

    def close(self):
        pass


old_socket = simfleet.socket.socket
simfleet.socket.socket = lambda *args: SimSocket()
fleet = simfleet.SimFleet(args, [device])
simfleet.socket.socket = old_socket


def sim_request(address, value=None):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    if value is not None:
        builder.add_arg(value)
    fleet.receive_contract(builder.build().dgram, ("10.0.0.8", 40000))


sim_request("/5/os/params")
check("simfleet params reply", fleet.sock.calls[-1] ==
      ("/os/params", [simfleet.DEFAULT_MANIFEST_TEXT], ("10.0.0.8", 5550)), repr(fleet.sock.calls[-1]))
sim_request("/5/os/report")
sim_report = json.loads(fleet.sock.calls[-1][1][0])
check("simfleet report reply", fleet.sock.calls[-1][0] == "/os/report"
      and sim_report["uid"] == device.mac and len(sim_report) == 11, repr(sim_report))
sim_request("/5/p/gain", 0.5)
check("simfleet declared param updates", device.gain == 0.5 and device.params["gain"] == 0.5)
old_params = dict(device.params)
logs = []
fleet.log = lambda target, message: logs.append(message)
sim_request("/5/p/nonsense", 1.0)
check("simfleet undeclared param dropped", device.params == old_params
      and logs == ["p/nonsense undeclared, dropped"], repr((device.params, logs)))
device.engine_dead = True
sim_request("/5/p/gain", 0.9)
check("simfleet engine-dead drops patch plane", device.gain == 0.5 and device.params["gain"] == 0.5,
      repr((device.gain, device.params)))
device.engine_dead = False

print()
if FAILURES:
    print("{} FAILURE(S): {}".format(len(FAILURES), FAILURES))
    sys.exit(1)
print("all checks passed")
