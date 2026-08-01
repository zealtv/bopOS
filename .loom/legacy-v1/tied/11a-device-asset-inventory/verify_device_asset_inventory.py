#!/usr/bin/env python3
"""Focused browser-free verification for durable device asset inventory."""

import asyncio
import json
import os
import sys
import tempfile
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
                os.path.join(ROOT, "tools"), os.path.join(ROOT, "dashboard")]

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
import identity  # noqa: E402
import simfleet  # noqa: E402
from osc_bridge import ASSET_REQUERY_SECONDS, OSCBridge  # noqa: E402
from state import InstallationState  # noqa: E402
from pythonosc.osc_message import OscMessage  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as target:
        target.write(content)


def clear_identity_cache():
    with identity._cache_lock:
        identity._file_hashes.clear()


class ReplySocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))


class DatagramSocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((OscMessage(data), target))

    def close(self):
        pass


def node_and_simulator_checks():
    with tempfile.TemporaryDirectory(prefix="bopos-assets-11a-") as temp:
        assets = os.path.join(temp, "assets")
        slot = os.path.join(assets, "belief-system-000")
        write(os.path.join(slot, "voices", "one.wav"), b"one")
        write(os.path.join(slot, ".ignored"), b"ignore")
        write(os.path.join(slot, "partial.part"), b"partial")
        os.symlink(os.path.join(slot, "voices", "one.wav"),
                   os.path.join(slot, "linked.wav"))

        clear_identity_cache()
        check("cold persistent cache loads no fabricated hashes",
              identity.load_hash_cache(assets) == 0)
        cold = identity.cached_directory_info(slot)
        check("cold inventory reports fresh counts but unknown fingerprint",
              cold == {"fingerprint": None, "files": 1, "bytes": 3}, repr(cold))

        identity.warm_hash_cache(assets)
        warm = identity.cached_directory_info(slot)
        expected = identity.fingerprint(slot)
        check("background warm resolves canonical slot fingerprint",
              warm["fingerprint"] == expected and len(expected) == 64, repr(warm))
        check("warm persists an invisible atomic cache",
              os.path.isfile(os.path.join(assets, ".hashcache.json")))

        clear_identity_cache()
        loaded = identity.load_hash_cache(assets)
        reloaded = identity.cached_directory_info(slot)
        check("node restart reloads the durable cache",
              loaded == 1 and reloaded["fingerprint"] == expected,
              repr((loaded, reloaded)))

        write(os.path.join(slot, "voices", "one.wav"), b"changed-out-of-band")
        edited = identity.cached_directory_info(slot)
        check("out-of-band edit invalidates identity but keeps counts fresh",
              edited["fingerprint"] is None and edited["files"] == 1
              and edited["bytes"] == len(b"changed-out-of-band"), repr(edited))
        identity.warm_hash_cache(assets)
        changed = identity.cached_directory_info(slot)["fingerprint"]
        check("warm rehashes changed signatures and publishes new identity",
              changed and changed != expected and changed == identity.fingerprint(slot))

        source = os.path.join(temp, "source")
        write(os.path.join(source, "nested", "fresh.wav"), b"fresh payload")
        uri = "file:" + urllib.parse.quote(source)
        ok, detail = fetcher.fetch(uri, "fetched-slot", assets)
        fetched = identity.cached_directory_info(os.path.join(assets, "fetched-slot"))
        check("successful fetch seeds a complete fingerprint immediately",
              ok and fetched["fingerprint"] is not None
              and fetched["files"] == 1 and fetched["bytes"] == len(b"fresh payload"),
              repr((detail, fetched)))

        write(os.path.join(assets, ".framework", "hidden"), b"x")
        os.symlink(slot, os.path.join(assets, "linked-slot"))
        old_manifest = identity.directory_manifest
        identity.directory_manifest = lambda *_args: (_ for _ in ()).throw(
            AssertionError("query path hashed content"))
        try:
            listing = bopos.installed_assets(assets)
        finally:
            identity.directory_manifest = old_manifest
        by_name = {item["name"]: item for item in listing}
        check("node listing excludes control entries and symlink slots",
              set(by_name) == {"belief-system-000", "fetched-slot"}, repr(listing))
        check("node query path uses cached facts without content hashing",
              all(set(item) == {"name", "fingerprint", "files", "bytes"}
                  for item in listing), repr(listing))

        old_root = bopos.ASSETS_ROOT
        bopos.ASSETS_ROOT = assets
        reply = ReplySocket()
        request = pyOSC3.OSCMessage("/7/os/assets")
        try:
            handled = bopos.handle_lan_datagram(
                request.getBinary(), ("10.0.0.9", 4000), reply,
                types.SimpleNamespace(id=7, uid="node-7"))
        finally:
            bopos.ASSETS_ROOT = old_root
        wire = json.loads(reply.calls[-1][0][2])
        check("real node serves compact /os/assets JSON by unicast",
              handled and reply.calls[-1][0][0] == "/os/assets"
              and {item["name"] for item in wire} == set(by_name), repr(reply.calls))

        sim = simfleet.SimFleet.__new__(simfleet.SimFleet)
        sim.assets_dir = assets
        sim.fetch_jobs = {}
        sim.fetch_active = {}
        sim.fetch_pending = {}
        sim.schedule = lambda *_args: None
        sim.sock = DatagramSocket()
        sim.args = types.SimpleNamespace(report_port=5550)
        sim.log = lambda *_args: None
        sim.send_rev = lambda *_args: None
        device = simfleet.Device("02:00:00:00:00:01", "sim-1", 7, "abcdef0")
        key = (device.mac, "uri", "belief-system-000")
        sim.fetch_jobs[key] = {"device": device, "slot": "belief-system-000",
                               "active": False, "ok": True, "requesters": []}
        sim.fetch_active[device.mac] = key
        sim.finish_fetch(key)
        snapshot = dict(device.asset_slots["belief-system-000"])
        check("simulated fetch snapshots the exact host catalog facts",
              snapshot["fingerprint"] == identity.fingerprint(slot)
              and snapshot["files"] == 1
              and snapshot["bytes"] == len(b"changed-out-of-band"), repr(snapshot))

        write(os.path.join(slot, "voices", "two.wav"), b"second")
        check("host edits do not mutate installed simulated snapshots",
              device.asset_slots["belief-system-000"] == snapshot)
        key = (device.mac, "uri-2", "belief-system-000")
        sim.fetch_jobs[key] = {"device": device, "slot": "belief-system-000",
                               "active": False, "ok": True, "requesters": []}
        sim.fetch_active[device.mac] = key
        sim.finish_fetch(key)
        check("simulated refetch refreshes observed identity",
              device.asset_slots["belief-system-000"]["fingerprint"]
              == identity.fingerprint(slot)
              and device.asset_slots["belief-system-000"]["fingerprint"]
              != snapshot["fingerprint"])

        sim.send_asset_list(device, ("127.0.0.1", 9000))
        sim_wire = json.loads(sim.sock.calls[-1][0].params[0])
        check("simulator replies with the contract asset shape",
              sim.sock.calls[-1][0].address == "/os/assets"
              and sim_wire[0]["name"] == "belief-system-000"
              and set(sim_wire[0]) == {"name", "fingerprint", "files", "bytes"},
              repr(sim_wire))
        sim.admin_verb(device, "dropassets", ["belief-system-000"],
                       ("127.0.0.1", 9000))
        check("simulated drop removes the installed slot",
              device.asset_slots == {}, repr(device.asset_slots))


async def dashboard_checks():
    with tempfile.TemporaryDirectory(prefix="bopos-assets-dashboard-") as temp:
        state = InstallationState(os.path.join(temp, "installation.json"))
        broadcasts = []
        bridge = OSCBridge(state, lambda kind, data: broadcasts.append((kind, data)),
                           0, 6660, "127.0.0.1")
        bridge.sender = DatagramSocket()
        uid = "02:00:00:00:00:11"
        device = state.ensure(uid)
        device.update(id=3, ip="10.0.0.3", online=True)
        check("dashboard starts with asset inventory unknown",
              device["assets"] is None and device["assets_observed_at"] is None)

        check("dashboard can issue the durable inventory query",
              bridge.request_assets(uid)
              and bridge.sender.calls[-1][0].address == "/3/os/assets")
        payload = [
            {"name": "current", "fingerprint": "a" * 64, "files": 4, "bytes": 40},
            {"name": "warming", "fingerprint": None, "files": 2, "bytes": 20},
            {"name": "field recordings", "fingerprint": "e" * 64,
             "files": 3, "bytes": 30},
            {"name": "broken", "fingerprint": "not-a-hash", "files": 1, "bytes": 1},
            {"name": "../unsafe", "fingerprint": "b" * 64, "files": 1, "bytes": 1},
        ]
        bridge.handle("/os/assets", [json.dumps(payload)], "10.0.0.3")
        assets = {item["name"]: item for item in device["assets"]}
        check("dashboard keeps valid entries and quarantines malformed ones",
              assets["current"]["fingerprint"] == "a" * 64
              and assets["warming"]["fingerprint"] is None
              and assets["field recordings"]["fingerprint"] == "e" * 64
              and assets["broken"]["unknown"] is True
              and "../unsafe" not in assets
              and len(device["assets_quarantine"]) == 2, repr(device))
        check("usable reply records an observed-at epoch",
              isinstance(device["assets_observed_at"], float)
              and device["assets_observed_at"] <= time.time())

        record = bridge._asset_requeries[uid]
        for _attempt in ASSET_REQUERY_SECONDS:
            timeout = record.get("timeout")
            if timeout:
                timeout.cancel()
                record["timeout"] = None
            bridge._requery_assets(uid, record)
            bridge._expire_request("assets", uid)
        check("null fingerprints use a capped four-step backoff",
              record["attempts"] == len(ASSET_REQUERY_SECONDS)
              and record.get("timeout") is None,
              repr(record))

        bridge.handle("/os/assets", [json.dumps([
            {"name": "warming", "fingerprint": "c" * 64,
             "files": 2, "bytes": 20}])], "10.0.0.3")
        check("resolved inventory cancels its requery generation",
              uid not in bridge._asset_requeries
              and device["assets"][0]["fingerprint"] == "c" * 64)

        bridge.request_assets(uid)
        bridge.handle("/os/assets", ["[]"], "10.0.0.3")
        check("observed empty inventory remains distinct from unknown",
              device["assets"] == [] and device["assets_observed_at"] is not None)

        bridge.request_assets(uid)
        bridge.handle("/os/assets", ["{}"], "10.0.0.3")
        check("malformed whole reply cannot masquerade as empty",
              device["assets"] is None and device["assets_observed_at"] is None
              and device["assets_quarantine"])

        older_uid = "02:00:00:00:00:12"
        older = state.ensure(older_uid)
        older.update(id=4, ip="10.0.0.4", online=True)
        bridge.request_assets(older_uid)
        bridge._expire_request("assets", older_uid)
        check("older node silence remains inventory unknown",
              older["assets"] is None and older["assets_observed_at"] is None
              and older_uid not in bridge._asset_requeries)

        # A successful asset receipt immediately asks for durable observation;
        # the session receipt itself is never treated as installed state.
        device["assets"] = []
        before = len(bridge.sender.calls)
        bridge.fetch(uid, "http://host/assets/current/.manifest.json",
                     "current", "d" * 64)
        bridge.handle("/os/fetched", ["current", "ok"], "10.0.0.3")
        emitted = [call[0].address for call in bridge.sender.calls[before:]]
        check("asset fetch receipt triggers a fresh inventory query",
              "/3/os/fetch" in emitted and "/3/os/assets" in emitted
              and device["assets"] == [], repr(emitted))
        bridge._expire_request("assets", uid)

        before = len(bridge.sender.calls)
        bridge.handle("/os/rev", ["abcdef0", "persistent", uid], "10.0.0.3")
        emitted = [call[0].address for call in bridge.sender.calls[before:]]
        check("provisioning revision receipt refreshes asset observation",
              "/3/os/assets" in emitted, repr(emitted))

        discovered_uid = "02:00:00:00:00:13"
        state.data["seats"]["5"] = {
            "id": 5, "name": "discovered", "positions": [[0.0, 0.0]],
            "params": {}, "groups": [], "bound": discovered_uid,
        }
        before = len(bridge.sender.calls)
        bridge.handle("/hb", [discovered_uid, 5, "abcdef0", 1], "10.0.0.5")
        emitted = [call[0].address for call in bridge.sender.calls[before:]]
        check("device discovery requests asset inventory",
              "/5/os/assets" in emitted, repr(emitted))

        bridge.close()
        await state.close()


async def main():
    node_and_simulator_checks()
    await dashboard_checks()
    total = 27
    print("\n{}/{} passed".format(total - len(FAILURES), total))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
