"""Direct checks for the fetch-landing stitch.

Run with PYTHONPATH=<pylib>:python:python/io.
"""
import hashlib
import http.server
import json
import os
import sys
import tempfile
import threading
import time
import types
import urllib.parse

import pyOSC3

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
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
    def connect(self, target):
        pass

    def send(self, message):
        pass


class ReplySocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
sys.argv = ["helper.py", "unknown"]
import fetcher
import bopos as helper


for bad in ("../x", "/x", "a/../x", "C:\\x"):
    try:
        fetcher.safe_path(bad)
        rejected = False
    except ValueError:
        rejected = True
    check("safe_path rejects {}".format(bad), rejected)

bad_manifests = ({}, {"files": "x"}, {"files": [{"path": "../x", "size": 1,
                  "sha256": "0" * 64}]}, {"files": [{"path": "x", "size": -1,
                  "sha256": "0" * 64}]})
for index, value in enumerate(bad_manifests):
    try:
        fetcher.parse_manifest(value)
        rejected = False
    except ValueError:
        rejected = True
    check("manifest validation {}".format(index + 1), rejected)


class AssetHandler(http.server.BaseHTTPRequestHandler):
    root = None
    manifest_hits = 0
    ranges = []
    break_big = False

    def do_GET(self):
        relative = urllib.parse.unquote(self.path.split("?", 1)[0]).lstrip("/")
        if relative == ".manifest.json":
            type(self).manifest_hits += 1
            data = open(os.path.join(self.root, relative), "rb").read()
        else:
            data = open(os.path.join(self.root, relative), "rb").read()
        range_header = self.headers.get("Range")
        if range_header:
            type(self).ranges.append(range_header)
            offset = int(range_header.split("=")[1].split("-")[0])
            data = data[offset:]
            self.send_response(206)
        else:
            self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if relative == "big.bin" and self.break_big:
            type(self).break_big = False
            self.wfile.write(data[:len(data) // 2])
            self.wfile.flush()
            self.connection.shutdown(1)
        else:
            self.wfile.write(data)

    def log_message(self, format, *args):
        pass


def write_manifest(root, names):
    files = []
    for name in names:
        path = os.path.join(root, name)
        data = open(path, "rb").read()
        files.append({"path": name, "size": len(data),
                      "sha256": hashlib.sha256(data).hexdigest()})
    with open(os.path.join(root, ".manifest.json"), "w") as target:
        json.dump({"files": files}, target)


with tempfile.TemporaryDirectory() as root:
    served, assets = os.path.join(root, "served"), os.path.join(root, "assets")
    os.makedirs(served)
    with open(os.path.join(served, "one.txt"), "wb") as target:
        target.write(b"one")
    with open(os.path.join(served, "two.txt"), "wb") as target:
        target.write(b"two")
    write_manifest(served, ["one.txt", "two.txt"])
    AssetHandler.root = served
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), AssetHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    uri = "http://127.0.0.1:{}/.manifest.json".format(server.server_port)
    ok, detail = fetcher.fetch(uri, "pack", assets)
    one = os.path.join(assets, "pack", "one.txt")
    check("http fresh fetch", ok and open(one, "rb").read() == b"one", detail)
    mtime = os.stat(one).st_mtime_ns
    check("http second fetch no-op", fetcher.fetch(uri, "pack", assets)[0]
          and os.stat(one).st_mtime_ns == mtime)
    time.sleep(0.01)
    with open(os.path.join(served, "one.txt"), "wb") as target:
        target.write(b"changed")
    write_manifest(served, ["one.txt"])
    check("http diff and prune", fetcher.fetch(uri, "pack", assets)[0]
          and open(one, "rb").read() == b"changed"
          and not os.path.exists(os.path.join(assets, "pack", "two.txt")))

    big = os.urandom(1024 * 1024)
    with open(os.path.join(served, "big.bin"), "wb") as target:
        target.write(big)
    write_manifest(served, ["big.bin"])
    AssetHandler.break_big = True
    AssetHandler.ranges = []
    check("http Range resume", fetcher.fetch(uri, "resume", assets)[0]
          and fetcher.sha256(os.path.join(assets, "resume", "big.bin")) == hashlib.sha256(big).hexdigest()
          and bool(AssetHandler.ranges), repr(AssetHandler.ranges))

    local = os.path.join(root, "local")
    os.makedirs(local)
    with open(os.path.join(local, "local.txt"), "w") as target:
        target.write("local")
    stale_dir = os.path.join(assets, "local")
    os.makedirs(stale_dir)
    open(os.path.join(stale_dir, "stale"), "w").close()
    file_uri = "file:" + urllib.parse.quote(local)
    check("file sync and prune", fetcher.fetch(file_uri, "local", assets)[0]
          and os.path.isfile(os.path.join(stale_dir, "local.txt"))
          and not os.path.exists(os.path.join(stale_dir, "stale")))

    old_bopos = helper.BOPOS_DIR
    helper.BOPOS_DIR = root
    reply = ReplySocket()
    message = pyOSC3.OSCMessage("/5/os/fetch")
    message.append(uri, "s")
    message.append("samplepacks", "s")
    before = AssetHandler.manifest_hits
    helper.handle_lan_datagram(message.getBinary(), ("10.0.0.8", 4000), reply,
                               types.SimpleNamespace(id=5))
    helper.handle_lan_datagram(message.getBinary(), ("10.0.0.9", 4000), reply,
                               types.SimpleNamespace(id=5))
    deadline = time.time() + 5
    while len(reply.calls) < 2 and time.time() < deadline:
        time.sleep(0.02)
    check("helper coalesces and replies", len(reply.calls) == 2
          and AssetHandler.manifest_hits == before + 1
          and all(call[0][3] == "ok" for call in reply.calls), repr(reply.calls))
    bad = pyOSC3.OSCMessage("/5/os/fetch")
    bad.append(uri, "s")
    bad.append("../evil", "s")
    helper.handle_lan_datagram(bad.getBinary(), ("10.0.0.8", 4000), reply,
                               types.SimpleNamespace(id=5))
    check("helper bad slot immediate err", reply.calls[-1][0][2:] == ["../evil", "err"])
    helper.BOPOS_DIR = old_bopos
    server.shutdown()

# Simfleet's receive_contract is covered in the patch-manifest-style setup used
# by its contract suite; exercise fetch validation without opening a real port.
sys.path.insert(0, os.path.join(helper.BOPOS_DIR, "tools"))
import simfleet
from pythonosc import osc_message, osc_message_builder

args = types.SimpleNamespace(protocol="v1", cmd_port=0, target="127.0.0.1", report_port=5550,
                             drop=0.0, jitter_ms=0.0, legacy_reports=False, state_dir=None,
                             hb_interval=10.0, boot_secs=1.0)
device = simfleet.Device("02:00:00:00:00:05", "sim5", 5, "abc1234")
device.state = "running"


class SimSocket:
    def __init__(self): self.calls = []
    def sendto(self, data, target):
        message = osc_message.OscMessage(data)
        self.calls.append((message.address, list(message.params), target))
    def setsockopt(self, *args): pass
    def bind(self, target): pass
    def setblocking(self, value): pass


old_socket = simfleet.socket.socket
simfleet.socket.socket = lambda *args: SimSocket()
fleet = simfleet.SimFleet(args, [device])
simfleet.socket.socket = old_socket


def sim_fetch(uri, slot):
    builder = osc_message_builder.OscMessageBuilder(address="/5/os/fetch")
    builder.add_arg(uri, arg_type="s")
    builder.add_arg(slot, arg_type="s")
    fleet.receive_contract(builder.build().dgram, ("10.0.0.8", 4000))


sim_fetch("ftp://bad", "slot")
check("simfleet fetch err", fleet.sock.calls[-1][1] == ["slot", "err"])
sim_fetch("http://source/manifest", "slot")
while fleet.events:
    _when, _sequence, callback, values = fleet.events.pop(0)
    callback(*values)
check("simfleet fetch ok", fleet.sock.calls[-1][1] == ["slot", "ok"])

print()
if FAILURES:
    print("{} FAILURE(S): {}".format(len(FAILURES), FAILURES))
    sys.exit(1)
print("all checks passed")
