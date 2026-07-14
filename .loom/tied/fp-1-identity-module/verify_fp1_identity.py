#!/usr/bin/env python3
"""Browser-free verification for fp-1: shared patch content identity."""

import hashlib
import heapq
import json
import os
import shutil
import sys
import tempfile
import types

sys.dont_write_bytecode = True


def repo_root():
    path = os.path.realpath(os.path.dirname(__file__))
    while path != os.path.dirname(path):
        if os.path.isfile(os.path.join(path, "tools", "simfleet.py")):
            return path
        path = os.path.dirname(path)
    raise RuntimeError("repository root not found")


ROOT = repo_root()
sys.path[:0] = [ROOT, os.path.join(ROOT, "python"), os.path.join(ROOT, "python", "io"),
                os.path.join(ROOT, "tools"), os.path.join(ROOT, "dashboard")]

import identity  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def reference_fingerprint(root):
    """The pre-extraction dashboard algorithm, verbatim, cache-free: the
    independent oracle proving identity.py did not change any byte of it."""
    files = []
    for directory, dirs, names in os.walk(root):
        dirs[:] = sorted(name for name in dirs
                         if not name.startswith(".")
                         and not os.path.islink(os.path.join(directory, name)))
        for name in sorted(names):
            if (name.startswith(".") or name.endswith(".part")
                    or os.path.islink(os.path.join(directory, name))):
                continue
            path = os.path.join(directory, name)
            hasher = hashlib.sha256()
            with open(path, "rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    hasher.update(chunk)
            files.append({"path": os.path.relpath(path, root).replace(os.sep, "/"),
                          "size": os.stat(path).st_size, "sha256": hasher.hexdigest()})
    files.sort(key=lambda item: item["path"])
    canonical = json.dumps({"files": files}, sort_keys=True,
                           separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


HEX64 = lambda value: isinstance(value, str) and len(value) == 64 and all(  # noqa: E731
    ch in "0123456789abcdef" for ch in value)


# -- 1. identity.py vs the dashboard's directory_info over patches/demo-pd --
import server  # noqa: E402  (dashboard/server.py)

demo = os.path.join(ROOT, "patches", "demo-pd")
info = server.directory_info(os.path.join(ROOT, "patches"), "demo-pd", "patch")
check("dashboard directory_info matches identity.fingerprint",
      info["fingerprint"] == identity.fingerprint(demo), repr(info["fingerprint"]))
check("demo-pd fingerprint matches the pre-extraction algorithm",
      info["fingerprint"] == reference_fingerprint(demo), repr(info["fingerprint"]))

# -- 2/3. synthetic twins, drift, and cache freshness --
with tempfile.TemporaryDirectory() as root:
    plain = os.path.join(root, "plain")
    twin = os.path.join(root, "twin")
    os.makedirs(os.path.join(plain, "nested"))
    for base in ("a.txt", os.path.join("nested", "b.wav")):
        with open(os.path.join(plain, base), "w") as target:
            target.write("content of " + base)
    shutil.copytree(plain, twin)
    os.makedirs(os.path.join(twin, ".git", "objects"))
    with open(os.path.join(twin, ".git", "config"), "w") as target:
        target.write("[core]")
    with open(os.path.join(twin, ".hidden"), "w") as target:
        target.write("dot")
    with open(os.path.join(twin, "a.txt.part"), "w") as target:
        target.write("partial")
    check("git/dot/.part tree fingerprints identically to its plain twin",
          identity.fingerprint(twin) == identity.fingerprint(plain))
    check("synthetic fingerprint matches the pre-extraction algorithm",
          identity.fingerprint(plain) == reference_fingerprint(plain))

    before = identity.fingerprint(plain)
    check("repeat fingerprint is stable (cache hit)",
          identity.fingerprint(plain) == before)
    with open(os.path.join(plain, "a.txt"), "w") as target:
        target.write("edited content")
    after = identity.fingerprint(plain)
    check("editing one file changes the fingerprint", after != before)
    check("cache returns the fresh post-edit value",
          after == reference_fingerprint(plain), repr(after))

# -- 4. node listing shape via bopos.installed_patches --
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
import manifest  # noqa: E402

with tempfile.TemporaryDirectory() as root:
    patches = os.path.join(root, "patches")
    live = os.path.join(patches, "live")
    os.makedirs(live)
    with open(os.path.join(live, "main.bin"), "w") as target:
        target.write("payload")
    with open(os.path.join(live, manifest.MANIFEST_NAME), "w") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": [],
                   "caps": [], "slots": []}, target)
    os.makedirs(os.path.join(live, ".git"))
    with open(os.path.join(patches, "active_patch.txt"), "w") as target:
        target.write("live\n")

    old_bopos_dir, old_active = bopos.BOPOS_DIR, bopos.active_patch_path
    bopos.BOPOS_DIR = root
    bopos.active_patch_path = lambda: live
    listing = bopos.installed_patches()
    bopos.BOPOS_DIR, bopos.active_patch_path = old_bopos_dir, old_active

    entry = {item["name"]: item for item in listing}.get("live", {})
    check("installed_patches entry carries a valid fingerprint",
          HEX64(entry.get("fingerprint")), repr(listing))
    check("node fingerprint equals the host walker's (git dir ignored)",
          entry.get("fingerprint") == reference_fingerprint(live), repr(entry))
    check("node listing keeps the declared v1.3 shape",
          entry.get("active") is True and entry.get("git") is True
          and entry.get("manifest") is True, repr(entry))

# -- 5. dashboard cleaner keeps valid fingerprints and drops junk --
import osc_bridge  # noqa: E402

good = "a" * 64
state = types.SimpleNamespace(devices={"uid-1": {"uid": "uid-1", "ip": "10.0.0.7"}})
events = []
bridge = osc_bridge.OSCBridge(state, lambda kind, data: events.append((kind, data)),
                              5550, 6660, "127.0.0.1")
wire = [{"name": "keep", "active": True, "git": False, "manifest": True,
         "fingerprint": good},
        {"name": "junk-short", "active": False, "git": False, "manifest": True,
         "fingerprint": "abc123"},
        {"name": "junk-case", "active": False, "git": False, "manifest": True,
         "fingerprint": "A" * 64},
        {"name": "junk-type", "active": False, "git": False, "manifest": True,
         "fingerprint": 7},
        {"name": "absent", "active": False, "git": False, "manifest": True}]
bridge.handle("/os/patches", [json.dumps(wire)], "10.0.0.7")
cleaned = {item["name"]: item for item in state.devices["uid-1"]["patches"]}
check("cleaner keeps a valid 64-hex fingerprint",
      cleaned["keep"].get("fingerprint") == good, repr(cleaned))
check("cleaner drops junk fingerprints and tolerates absence",
      all("fingerprint" not in cleaned[name]
          for name in ("junk-short", "junk-case", "junk-type", "absent")),
      repr(cleaned))
bridge.close()

# -- 6. simfleet reports fingerprints on /os/patches --
import simfleet  # noqa: E402
from pythonosc import osc_message, osc_message_builder  # noqa: E402


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

    def settimeout(self, _value):
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


calls = sim_request("/5/os/patches")
sim_patches = {item["name"]: item for item in json.loads(calls[-1][1][0])}
check("sim demo-pd reports the real host fingerprint",
      sim_patches.get("demo-pd", {}).get("fingerprint") == identity.fingerprint(demo),
      repr(sim_patches))

sim_request("/5/os/fetch", ("file:/source", "patch:fakepatch"))
while fleet.events:
    _when, _sequence, callback, values = heapq.heappop(fleet.events)
    callback(*values)
calls = sim_request("/5/os/patches")
sim_patches = {item["name"]: item for item in json.loads(calls[-1][1][0])}
check("sim fetched fake patch reports a stable fake fingerprint",
      sim_patches.get("fakepatch", {}).get("fingerprint")
      == hashlib.sha256(b"fakepatch").hexdigest(), repr(sim_patches))

sim_request("/5/os/addpatch", ("someuser", "gitfake"))
while fleet.events:
    _when, _sequence, callback, values = heapq.heappop(fleet.events)
    callback(*values)
calls = sim_request("/5/os/patches")
sim_patches = {item["name"]: item for item in json.loads(calls[-1][1][0])}
check("sim git-installed fake reports a 64-hex fingerprint",
      HEX64(sim_patches.get("gitfake", {}).get("fingerprint")), repr(sim_patches))

sim_request("/5/os/report")
report = json.loads(fleet.sock.calls[-1][1][0])
check("sim report speaks contract v1.4", report["contract_version"] == "1.4",
      repr(report))

# -- audition mirror: real host directories get the real identity --
import audition  # noqa: E402

audition_args = types.SimpleNamespace(
    manifest=os.path.join(ROOT, "patches", "demo-pd", "bopos.patch.json"),
    patches_dir=os.path.join(ROOT, "patches"),
    devices=1, id_base=0, engine_port_base=17000, bind="127.0.0.1",
    cmd_port=0, engine_host="127.0.0.1", target="127.0.0.1", report_port=0)
old_audition_socket = audition.socket.socket
audition.socket.socket = lambda *_args: SimSocket()
rig = audition.AuditionRig(audition_args)
audition.socket.socket = old_audition_socket
audition_listing = {item["name"]: item for item in rig.patch_listing()}
check("audition listing carries the real host fingerprint",
      audition_listing.get("demo-pd", {}).get("fingerprint")
      == identity.fingerprint(demo), repr(audition_listing))

print()
if FAILURES:
    print("{} FAILURE(S): {}".format(len(FAILURES), FAILURES))
    raise SystemExit(1)
print("all checks passed")
