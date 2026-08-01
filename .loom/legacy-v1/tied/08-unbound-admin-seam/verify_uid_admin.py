#!/usr/bin/env python3
"""Focused UID-admin contract, helper, tooling and Dashboard regression."""

import json
import asyncio
import os
import random
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

from playwright.sync_api import sync_playwright
from pythonosc.osc_message_builder import OscMessageBuilder

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "python"))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, os.path.join(REPO, "dashboard"))

FAILURES = []
RESERVED = set()


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
          " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def packet(address, *args):
    builder = OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


def free_port(kind):
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        if (kind, port) in RESERVED:
            continue
        probe = socket.socket(socket.AF_INET, kind)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            probe.close()
            continue
        probe.close()
        RESERVED.add((kind, port))
        return port
    raise RuntimeError("cannot reserve localhost port")


def wait_until(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.05)
    return False


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


# Import the real helper without opening its legacy OSC server.
import pyOSC3


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
sys.argv = ["bopos.py", "unknown"]
import bopos
from store import Store


def helper_packet(address, *args):
    message = pyOSC3.OSCMessage(address)
    for value in args:
        message.append(value)
    return message.getBinary()


class Node:
    def __init__(self, root):
        self.uid = "node-a"
        self.id = 7
        self.version = "abc1234"
        self.update_model = "persistent"
        self.config = {"AUDIO_CHANNELS": "2", "MIXER_CONTROL": None}
        self.store = Store(os.path.join(root, "store"))
        self.store.put("assignment", [7, "stage-left", 1.0, 2.0])
        self.elements = [[1.0, 2.0]]
        self.mixer_control = None
        self.muted_via_stop = False
        self.reports = {}
        self.reports_lock = threading.Lock()


def helper_checks():
    with tempfile.TemporaryDirectory(prefix="bopos-uid-helper-") as root:
        state = Node(root)
        reply = ReplySocket()
        calls = []
        original_reboot = bopos.LIFECYCLE_VERBS["reboot"]
        bopos.LIFECYCLE_VERBS["reboot"] = lambda *args, **kwargs: calls.append("reboot")
        try:
            handled = bopos.handle_lan_datagram(
                helper_packet("/all/os/to", "other", "reboot"),
                ("10.0.0.8", 4000), reply, state)
            check("helper ignores a different uid", handled and not calls and not reply.calls)

            handled = bopos.handle_lan_datagram(
                helper_packet("/all/os/to", "node-a", "patch", "demo-pd"),
                ("10.0.0.8", 4000), reply, state)
            check("helper rejects verbs outside the seven-verb allowlist",
                  not handled and not calls and not reply.calls)

            handled = bopos.handle_lan_datagram(
                helper_packet("/all/os/to", "node-a", "reboot", "extra"),
                ("10.0.0.8", 4000), reply, state)
            check("helper rejects nonzero arity", not handled and not calls)

            handled = bopos.handle_lan_datagram(
                helper_packet("/all/os/to", "node-a", "reboot"),
                ("10.0.0.8", 4000), reply, state)
            check("helper dispatches one targeted lifecycle action",
                  handled and wait_until(lambda: calls == ["reboot"], 2), repr(calls))
            check("targeted lifecycle receipt carries uid",
                  bool(reply.calls) and reply.calls[-1][0][0] == "/os/rev"
                  and reply.calls[-1][0][-1] == "node-a", repr(reply.calls))

            bopos.client.sent[:] = []
            bopos.hb_wake.clear()
            handled = bopos.handle_lan_datagram(
                helper_packet("/all/os/to", "node-a", "unassign"),
                ("10.0.0.8", 4000), reply, state)
            check("unassign clears runtime and engine identity",
                  handled and state.id == -1 and state.elements == []
                  and ["/id", ",f", -1.0] in bopos.client.sent,
                  repr((state.id, state.elements, bopos.client.sent)))
            check("unassign persists a seed-blocking tombstone",
                  state.store.get("assignment") == [-1, "stage-left"]
                  and _seed_resolves_unassigned(root, state.store),
                  repr(state.store.get("assignment")))
            check("unassign wakes its heartbeat acknowledgement", bopos.hb_wake.is_set())
            check("unassign is idempotent",
                  bopos.handle_lan_datagram(
                      helper_packet("/all/os/to", "node-a", "unassign"),
                      ("10.0.0.8", 4000), reply, state)
                  and state.store.get("assignment") == [-1, "stage-left"])

            class FailingStore:
                def get(self, _key):
                    return [7, "stage-left"]

                def put(self, _key, _value):
                    return False

            state.id, state.elements, state.store = 7, [[1.0, 2.0]], FailingStore()
            bopos.client.sent[:] = []
            bopos.hb_wake.clear()
            handled = bopos.handle_lan_datagram(
                helper_packet("/all/os/to", "node-a", "unassign"),
                ("10.0.0.8", 4000), reply, state)
            check("failed tombstone write leaves runtime assignment intact",
                  not handled and state.id == 7 and state.elements == [[1.0, 2.0]]
                  and not bopos.client.sent and not bopos.hb_wake.is_set())
        finally:
            bopos.LIFECYCLE_VERBS["reboot"] = original_reboot


def audition_checks():
    import audition
    rig = audition.AuditionRig.__new__(audition.AuditionRig)
    rig.nodes = [audition.VirtualNode(0, -1, "audition-0001", 18001),
                 audition.VirtualNode(1, -1, "audition-0002", 18002)]
    identified = []
    heartbeats = []
    rig.send_engine = lambda node, address, args=(): identified.append((node.uid, address, args))
    rig.send_id = lambda node: None
    rig.send_matrix = lambda node: None
    rig.send_heartbeat = lambda node: heartbeats.append((node.uid, node.device_id))
    rig.relay(packet("/all/os/to", "audition-0002", "identify"), ("127.0.0.1", 4000))
    check("audition envelope identifies only the exact uid",
          identified == [("audition-0002", "/notify", ("identify",))], repr(identified))
    rig.nodes[1].device_id = 4
    rig.nodes[1].positions = ((1.0, 2.0),)
    rig.relay(packet("/all/os/to", "audition-0002", "unassign"), ("127.0.0.1", 4000))
    check("audition unassign returns only its target to id -1",
          rig.nodes[0].device_id == -1 and rig.nodes[1].device_id == -1
          and rig.nodes[1].positions == () and heartbeats == [("audition-0002", -1)],
          repr((rig.nodes, heartbeats)))


def _seed_resolves_unassigned(root, store):
    seed = os.path.join(root, "bopos.devices")
    with open(seed, "w", encoding="utf-8") as target:
        target.write("node-a,seed-name,7\n")
    return bopos.resolve_id("node-a", seed, store) == -1


def bridge_handshake_check():
    from osc_bridge import OSCBridge
    from state import InstallationState

    async def scenario(root):
        state = InstallationState(os.path.join(root, "installation.json"))
        state.seats["7"] = {"id": 7, "name": "Seat 7", "positions": [],
                            "params": {}, "bound": "node-a"}
        device = state.ensure("node-a")
        device.update(id=7, online=True, ip="127.0.0.1", version="old",
                      engine_alive=1, last_seen=time.time())
        bridge = OSCBridge(state, lambda *_args: None, 15550, 16660, "127.0.0.1")
        sent, replayed = [], []
        bridge.uid_command = lambda uid, verb, args=(): sent.append((uid, verb, tuple(args)))
        bridge.assign = lambda *args: replayed.append(args)
        task = asyncio.create_task(bridge.unassign("node-a", timeout=.5))
        await asyncio.sleep(0)
        bridge.handle("/hb", ["node-a", -1, "new", 1], "127.0.0.1")
        acknowledged = await task
        return acknowledged, sent, replayed, device["id"]

    with tempfile.TemporaryDirectory(prefix="bopos-unassign-handshake-") as root:
        acknowledged, sent, replayed, device_id = asyncio.run(scenario(root))
    check("dashboard handshake suppresses assign replay until id -1 acknowledgement",
          acknowledged and sent == [("node-a", "unassign", ())]
          and replayed == [] and device_id == -1,
          repr((acknowledged, sent, replayed, device_id)))


def e2e_checks():
    with tempfile.TemporaryDirectory(prefix="bopos-uid-e2e-") as root:
        assets = os.path.join(root, "assets")
        patches = os.path.join(root, "patches")
        node_state = os.path.join(root, "nodes")
        os.makedirs(assets)
        os.makedirs(patches)
        os.makedirs(node_state)
        state_file = os.path.join(root, "installation.json")
        bound_uid = "02:53:49:4d:00:01"
        with open(state_file, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "uid", "seats": {
                "0": {"id": 0, "name": "Seat 0", "positions": [],
                      "params": {}, "bound": bound_uid},
            }}, target)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM)
        dashboard_log_path = os.path.join(root, "dashboard.log")
        fleet_log_path = os.path.join(root, "fleet.log")
        dashboard_log = open(dashboard_log_path, "w", encoding="utf-8")
        fleet_log = open(fleet_log_path, "w", encoding="utf-8")
        dashboard = fleet = None
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            dashboard = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(command_port),
                "--osc-target", "127.0.0.1", "--state-file", state_file,
                "--assets-dir", assets, "--patches-dir", patches,
            ], cwd=REPO, stdout=dashboard_log, stderr=subprocess.STDOUT)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "3", "--unassigned", "3", "--cmd-port", str(command_port),
                "--report-port", str(listen_port), "--target", "127.0.0.1",
                "--state-dir", node_state, "--hb-interval", ".5",
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)
            base_url = f"http://127.0.0.1:{http_port}"
            check("dashboard starts", wait_until(lambda: _http_ready(base_url, dashboard), 10))
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1400, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function("() => Object.keys(installation.devices||{}).length === 3")
                page.click("#tab-button-devices")
                page.evaluate(
                    "([uid]) => ws.send('action', {uid, verb:'restart-engine'})",
                    [bound_uid])
                check("bound individual action also uses exact uid routing",
                      wait_until(lambda: _log_has(fleet_log_path,
                                                 "Seat 0 id=0 os/restart-engine"), 5)
                      and not _log_has(fleet_log_path, "sim2 id=-1 os/restart-engine")
                      and not _log_has(fleet_log_path, "sim3 id=-1 os/restart-engine"))

                uid = "02:53:49:4d:00:02"
                page.click(f'#unassigned .device-row[data-uid="{uid}"]')
                page.wait_for_function(
                    f"() => installation.devices[{json.dumps(uid)}]?.report?.contract_version === '1.5'")
                check("unbound detail exposes the four safe individual actions",
                      page.locator("#detail [data-action]").count() == 4)
                check("unbound report is uid-targeted and contract-current",
                      "1.5" in page.locator("#detail").inner_text())

                page.click("#detail [data-identify]")
                check("dashboard identify isolates one of multiple id -1 nodes",
                      wait_until(lambda: _log_has(fleet_log_path, "sim2 id=-1 identify"), 5)
                      and not _log_has(fleet_log_path, "sim1 id=0 identify")
                      and not _log_has(fleet_log_path, "sim3 id=-1 identify"))

                page.click('#detail [data-action="restart-engine"]')
                check("dashboard lifecycle action isolates one unbound id -1 node",
                      wait_until(lambda: _log_has(fleet_log_path,
                                                 "sim2 id=-1 os/restart-engine"), 5)
                      and not _log_has(fleet_log_path, "sim3 id=-1 os/restart-engine"))

                sender.sendto(packet("/all/os/assign", uid, 7, "sim1", 1.0, 2.0),
                              ("127.0.0.1", command_port))
                state_path = os.path.join(node_state, uid.replace(":", "-") + ".json")
                check("simfleet target accepts an ordinary persisted assignment",
                      wait_until(lambda: _json_id(state_path) == 7, 5))
                sender.sendto(packet("/all/os/to", uid, "unassign"),
                              ("127.0.0.1", command_port))
                check("simfleet UID unassign persists id -1 and acknowledges",
                      wait_until(lambda: _json_id(state_path) == -1, 5)
                      and wait_until(lambda: page.evaluate(
                          f"installation.devices[{json.dumps(uid)}]?.id") == -1, 5))
                check("excluded content verb changes no target state",
                      _excluded_verb_unchanged(sender, command_port, fleet_log_path, uid))
                check("browser emitted no page errors", not errors, repr(errors))
                browser.close()
        finally:
            sender.close()
            stop(fleet)
            stop(dashboard)
            fleet_log.close()
            dashboard_log.close()
        server_text = open(dashboard_log_path, encoding="utf-8").read()
        check("managed processes exit cleanly",
              dashboard is not None and dashboard.returncode in (0, -15)
              and fleet is not None and fleet.returncode in (0, -15)
              and "Application shutdown complete" in server_text)


def _http_ready(url, process):
    if process.poll() is not None:
        return False
    try:
        urllib.request.urlopen(url, timeout=.2).close()
        return True
    except OSError:
        return False


def _log_has(path, text):
    try:
        return text in open(path, encoding="utf-8").read()
    except OSError:
        return False


def _json_id(path):
    try:
        return json.load(open(path, encoding="utf-8")).get("id")
    except (OSError, ValueError):
        return None


def _excluded_verb_unchanged(sender, port, log_path, uid):
    before = open(log_path, encoding="utf-8").read()
    sender.sendto(packet("/all/os/to", uid, "patch", "demo-pd"),
                  ("127.0.0.1", port))
    time.sleep(.3)
    after = open(log_path, encoding="utf-8").read()
    return after.count("os/patch") == before.count("os/patch")


def main():
    helper_checks()
    audition_checks()
    bridge_handshake_check()
    e2e_checks()
    total = 24
    print(f"\n{total - len(FAILURES)}/{total} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
