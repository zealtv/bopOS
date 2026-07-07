"""Direct checks for the assign-persistence stitch.

Run with PYTHONPATH=<pylib>:python:python/io (pylib needs pyOSC3 + pythonosc).
"""
import json
import os
import sys
import tempfile

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


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
sys.argv = ["helper.py", "unknown"]
import helper
from store import Store

# --- A. Store ----------------------------------------------------------------
with tempfile.TemporaryDirectory() as root:
    store_dir = os.path.join(root, "store")
    store = Store(store_dir)
    check("store put/get mixed types",
          store.put("k1", [7, 0.5, "name"]) and store.get("k1") == [7, 0.5, "name"],
          repr(store.get("k1")))
    check("store no tmp artifact", os.listdir(store_dir) == ["k1"], repr(os.listdir(store_dir)))
    check("store invalid key rejected",
          not store.put("../evil", [1]) and store.get("../evil") == [])
    check("store dotfile key rejected", not store.put(".hidden", [1]))
    check("store missing key empty", store.get("nope") == [])
    store.put("k1", [8])
    check("store overwrite is full-state", store.get("k1") == [8])
    store.delete("k1")
    check("store delete", store.get("k1") == [])

    ram = Store(os.path.join(root, "ram"), persistent=False)
    ram.put("k", [1, "x"])
    check("ephemeral store keeps values in RAM", ram.get("k") == [1, "x"])
    check("ephemeral store writes nothing to disk", not os.path.exists(os.path.join(root, "ram")))

# --- B. Boot resolution -------------------------------------------------------
with tempfile.TemporaryDirectory() as root:
    devices = os.path.join(root, "bopos.devices")
    with open(devices, "w") as target:
        target.write("aa:bb,seedname,7\n")
    store = Store(os.path.join(root, "store"))
    check("resolve_id seed without store", helper.resolve_id("aa:bb", devices, store) == 7)
    store.put("assignment", [42, "assignedname", 1.0, 2.0])
    check("resolve_id persisted assignment wins", helper.resolve_id("aa:bb", devices, store) == 42)
    check("resolve_id unknown uid unassigned", helper.resolve_id("cc:dd", devices, Store(os.path.join(root, "s2"))) == -1)

# --- C. /os/assign ------------------------------------------------------------
class State:
    def __init__(self, uid="node-uid", device_id=-1, store=None):
        self.uid = uid
        self.id = device_id
        self.version = "a1b2c3d"
        self.config = {"HB_TARGET": "127.0.0.1", "HB_RSSI": "1", "MIXER_CONTROL": None,
                       "UPDATE_MODEL": "persistent"}
        self.mixer_control = None
        self.muted_via_stop = False
        self.store = store


class ReplySocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))


hostnames = []
old_set_hostname = helper.set_hostname
helper.set_hostname = lambda name: hostnames.append(name)

with tempfile.TemporaryDirectory() as root:
    state = State(store=Store(os.path.join(root, "store")))
    helper.client.sent[:] = []
    helper.hb_wake.clear()

    msg = pyOSC3.OSCMessage("/all/os/assign")
    for value, tag in (("node-uid", "s"), (5, "i"), ("voice5", "s"),
                       (1.5, "f"), (2.5, "f"), (0.0, "f"), (100.0, "f")):
        msg.append(value, tag)
    handled = helper.handle_lan_datagram(msg.getBinary(), ("10.0.0.9", 40000), ReplySocket(), state)
    check("assign applies id", handled and state.id == 5)
    check("assign sets hostname", hostnames == ["voice5"], repr(hostnames))
    check("assign tells engine /id", ["/id", ",f", 5.0] in helper.client.sent, repr(helper.client.sent))
    check("assign persists with positions",
          state.store.get("assignment") == [5, "voice5", 1.5, 2.5, 0.0, 100.0],
          repr(state.store.get("assignment")))
    check("assign wakes heartbeat", helper.hb_wake.is_set())

    handled_again = helper.handle_lan_datagram(msg.getBinary(), ("10.0.0.9", 40000), ReplySocket(), state)
    check("assign idempotent", handled_again and state.id == 5
          and state.store.get("assignment") == [5, "voice5", 1.5, 2.5, 0.0, 100.0])

    other = pyOSC3.OSCMessage("/all/os/assign")
    other.append("someone-else", "s")
    other.append(9, "i")
    other.append("other", "s")
    hostnames[:] = []
    handled = helper.handle_lan_datagram(other.getBinary(), ("10.0.0.9", 40000), ReplySocket(), state)
    check("assign uid mismatch ignored", not handled and state.id == 5 and not hostnames)

    # --- D. LAN store/load ------------------------------------------------------
    put = pyOSC3.OSCMessage("/5/os/store")
    put.append("preset", "s")
    put.append(3, "i")
    put.append(0.25, "f")
    put.append("warm", "s")
    check("LAN store persists", helper.handle_lan_datagram(put.getBinary(), ("10.0.0.9", 40000), ReplySocket(), state)
          and state.store.get("preset") == [3, 0.25, "warm"], repr(state.store.get("preset")))

    load = pyOSC3.OSCMessage("/5/os/load")
    load.append("preset", "s")
    reply = ReplySocket()
    helper.handle_lan_datagram(load.getBinary(), ("10.0.0.9", 40000), reply, state)
    check("LAN load replies typed unicast",
          reply.calls == [(["/os/load", ",sifs", "preset", 3, 0.25, "warm"], ("10.0.0.9", 5550))],
          repr(reply.calls))

    load2 = pyOSC3.OSCMessage("/5/os/load")
    load2.append("missing", "s")
    reply = ReplySocket()
    helper.handle_lan_datagram(load2.getBinary(), ("10.0.0.9", 40000), reply, state)
    check("LAN load missing key legal empty",
          reply.calls == [(["/os/load", ",s", "missing"], ("10.0.0.9", 5550))], repr(reply.calls))

    # --- E. localhost /store /load ---------------------------------------------
    old_state = helper.node_state
    helper.node_state = state
    helper.client.sent[:] = []
    helper.store_callback(args=["engine-key", 11, "hello"])
    check("localhost /store persists", state.store.get("engine-key") == [11, "hello"])
    helper.load_callback(args=["engine-key"])
    check("localhost /load replies to engine",
          helper.client.sent == [["/load", ",sis", "engine-key", 11, "hello"]],
          repr(helper.client.sent))
    helper.node_state = old_state

helper.set_hostname = old_set_hostname

# --- F. simfleet persistence --------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(helper.BOPOS_DIR + "/"), "tools"))
import types
import importlib
simfleet = importlib.import_module("simfleet")

with tempfile.TemporaryDirectory() as state_dir:
    args = types.SimpleNamespace(devices=3, devices_file=None, unresponsive=0, unassigned=3,
                                 wired=0, engine_dead=0, ephemeral=1, protocol="v1",
                                 version="a1b2c3d", state_dir=state_dir)
    with open(os.path.join(state_dir, "02-53-49-4d-00-01.json"), "w") as target:
        json.dump({"id": 12, "name": "stagefront", "positions": []}, target)
    with open(os.path.join(state_dir, "02-53-49-4d-00-03.json"), "w") as target:
        json.dump({"id": 13, "name": "ghost", "positions": []}, target)
    devices = simfleet.load_devices(args)
    check("simfleet persisted assignment overrides seed",
          devices[0].device_id == 12 and devices[0].hostname == "stagefront",
          repr([(d.device_id, d.hostname) for d in devices]))
    check("simfleet unassigned stays -1 without state file", devices[1].device_id == -1)
    check("simfleet ephemeral ignores persisted state",
          devices[2].ephemeral and devices[2].device_id == -1)

    devices[1].device_id = 4
    devices[1].hostname = "midstage"
    devices[1].save_assignment(state_dir, [0.0, 1.0])
    saved = json.load(open(devices[1].state_file(state_dir)))
    check("simfleet save_assignment round-trip",
          saved == {"id": 4, "name": "midstage", "positions": [0.0, 1.0]}, repr(saved))
    os.remove(devices[2].state_file(state_dir))  # planted for the ignore-check above
    devices[2].save_assignment(state_dir, [])
    check("simfleet ephemeral never persists",
          not os.path.exists(devices[2].state_file(state_dir)))

print()
if FAILURES:
    print("{} FAILURE(S): {}".format(len(FAILURES), FAILURES))
    sys.exit(1)
print("all checks passed")
