#!/usr/bin/env python3
"""Protocol/stub verification for the bopOS SuperCollider starter.

SuperCollider itself is optional on a development host. This verifies the
manifest, launcher selection, helper identity catch-up, documented SC receiver
surfaces, selector routing, element/point state, cues, and the final
gain * proximity * master relationship using real OSC datagrams.
"""
import ast
import json
import math
import os
import select
import socket
import sys
import tempfile
import threading
import time
from csv import reader

from pythonosc.osc_packet import OscPacket
from pythonosc.udp_client import SimpleUDPClient


HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent

TEMPLATE = os.path.join(REPO, "patches", "demo-sc")
FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


class EngineStub:
    """State-equivalent receiver for the surfaces implemented in main.scd."""

    def __init__(self):
        self.id = -1
        self.master = 1.0
        self.params = {"gain": 0.7, "frequency": 220.0}
        self.points = {}
        self.elements = {}
        self.cues = []
        self.running = True
        self.sockets = []
        for port in (16681,):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", port))
            sock.setblocking(False)
            self.sockets.append(sock)
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def loop(self):
        while self.running:
            readable, _, _ = select.select(self.sockets, [], [], 0.05)
            for sock in readable:
                data, _ = sock.recvfrom(65535)
                for timed in OscPacket(data).messages:
                    message = timed.message
                    self.handle(sock.getsockname()[1], message.address,
                                list(message.params))

    def handle(self, port, address, args):
        if port == 16681 and address == "/id" and args:
            self.id = int(args[0])
        elif port == 16681 and address == "/os/master" and args:
            self.master = min(max(float(args[0]), 0.0), 1.0)
        elif port == 16681 and address == "/pt" and len(args) >= 3:
            point, element, value = int(args[0]), int(args[1]), float(args[2])
            self.points[(point, element)] = value
            self.elements.setdefault(element, {"proximity": 0.0})
            if point == 0:
                self.elements[element]["proximity"] = value
        elif port == 16681 and address == "/cue" and args:
            self.cues.append(str(args[0]))
        elif port == 16681 and args:
            parts = [part for part in address.split("/") if part]
            if len(parts) == 2 and parts[0] == "p" and parts[1] in self.params:
                self.params[parts[1]] = args[0]

    def amplitude(self, element):
        return (float(self.params["gain"])
                * float(self.elements[element]["proximity"])
                * self.master)

    def close(self):
        self.running = False
        self.thread.join(timeout=1)
        for sock in self.sockets:
            sock.close()


def manifest_checks():
    sys.path.insert(0, os.path.join(REPO, "python"))
    import manifest
    loaded, error = manifest.load(TEMPLATE)
    check("SC manifest validates", error is None, str(error))
    check("launcher selects sclang main.scd",
          loaded is not None and loaded.get("engine") == "sclang"
          and loaded.get("entrypoint") == "main.scd", repr(loaded))
    params = {item["name"]: item for item in loaded.get("params", [])}
    check("template declares volume and promoted sound param",
          params.get("gain", {}).get("role") == "volume"
          and params.get("frequency", {}).get("facilitator") is True)


def source_checks():
    source = open(os.path.join(TEMPLATE, "main.scd"), encoding="utf-8").read()
    required = ("recvPort: 6661", "'/os/master'", "'/pt'", "'/cue'", "'/id'",
                "NetAddr(\"127.0.0.1\", 7770).sendMsg('/config')",
                "Lag.kr(master.clip(0, 1), 0.03)", "element.asInteger")
    check("SC source contains every provided-term receiver",
          all(token in source for token in required),
          repr([token for token in required if token not in source]))
    check("one sclang process boots one server and clones element Synths",
          "s.waitForBoot" in source and "ensureElement" in source
          and "Synth.before" in source)


def helper_identity_check():
    source_path = os.path.join(REPO, "python", "bopos.py")
    source = open(source_path, encoding="utf-8").read()
    tree = ast.parse(source)
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == "config_callback")

    class FakeMessage:
        def __init__(self, address):
            self.address = address
            self.values = []

        def append(self, value, tag=None):
            self.values.append((value, tag))

    class FakeClient:
        sent = []

        def send(self, message):
            self.sent.append(message)

    class State:
        uid = "not-in-seed"
        id = 37

    with tempfile.TemporaryDirectory() as temp:
        namespace = {"os": os, "reader": reader, "BOPOS_DIR": temp,
                     "node_state": State(), "OSCMessage": FakeMessage,
                     "client": FakeClient(), "set_hostname": lambda _name: None}
        exec(compile(ast.Module(body=[function], type_ignores=[]),
                     source_path, "exec"), namespace)
        namespace["config_callback"]()
    sent = FakeClient.sent
    check("helper /config returns persisted ID without bopos.devices",
          len(sent) == 1 and sent[0].address == "/id"
          and sent[0].values == [(37, "i")], repr(sent[0].values if sent else []))


def helper_relay_check():
    source_path = os.path.join(REPO, "python", "bopos.py")
    tree = ast.parse(open(source_path, encoding="utf-8").read())
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef)
                    and node.name == "handle_lan_datagram")
    relayed = []
    namespace = {
        "decodeOSC": lambda datagram: datagram,
        "expected_engine_name": lambda: "sclang",
        "selector_matches": lambda selector, device_id:
            selector == "all" or int(selector) == int(device_id),
        "relay_provided_term": lambda address, args:
            relayed.append((address, list(args))) or True,
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), source_path, "exec"), namespace)
    state = type("State", (), {"id": 7})()
    reply = object()
    handler = namespace["handle_lan_datagram"]
    check("helper relays matched master to non-PD engine",
          handler(["/all/os/master", ",f", 0.5], ("127.0.0.1", 1), reply, state)
          and relayed[-1] == ("/os/master", [0.5]), repr(relayed))
    check("helper relays matched patch param with selector stripped",
          handler(["/7/p/gain", ",f", 0.8], ("127.0.0.1", 1), reply, state)
          and relayed[-1] == ("/p/gain", [0.8]), repr(relayed))
    before = list(relayed)
    check("helper rejects another device's patch selector",
          not handler(["/8/p/gain", ",f", 0.1], ("127.0.0.1", 1), reply, state)
          and relayed == before)


def wire_checks():
    stub = EngineStub()
    local = SimpleUDPClient("127.0.0.1", 16681)
    try:
        local.send_message("/id", 7)
        local.send_message("/p/gain", 0.8)
        local.send_message("/p/frequency", 440.0)
        local.send_message("/os/master", 0.5)
        local.send_message("/pt", [0, 0, 0.25])
        local.send_message("/pt", [0, 1, 0.75])
        local.send_message("/cue", "downbeat")
        time.sleep(0.25)
        check("selector-stripped local parameters route",
              stub.id == 7 and math.isclose(stub.params["gain"], 0.8, rel_tol=1e-6)
              and math.isclose(stub.params["frequency"], 440.0, rel_tol=1e-6))
        check("0-based point scalars create independent elements",
              set(stub.elements) == {0, 1}
              and math.isclose(stub.elements[0]["proximity"], 0.25)
              and math.isclose(stub.elements[1]["proximity"], 0.75))
        check("final stage enacts raw gain x point x master",
              math.isclose(stub.amplitude(0), 0.1, rel_tol=1e-6)
              and math.isclose(stub.amplitude(1), 0.3, rel_tol=1e-6))
        check("scheduled bare cue reaches engine", stub.cues == ["downbeat"], repr(stub.cues))
    finally:
        stub.close()


def main():
    manifest_checks()
    source_checks()
    helper_identity_check()
    helper_relay_check()
    wire_checks()
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("SC starter protocol checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
