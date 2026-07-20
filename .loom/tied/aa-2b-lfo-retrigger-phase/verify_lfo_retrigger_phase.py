#!/usr/bin/env python3
"""Focused regression for non-free LFO phase across show-step retriggers."""

import json
import os
import subprocess
import sys
from unittest import mock

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "dashboard", "server.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "dashboard"))
sys.path.insert(0, REPO)

import osc_bridge as bridge_module  # noqa: E402
from osc_bridge import OSCBridge  # noqa: E402


FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


class FakeState:
    def __init__(self):
        self.data = {}
        self.seats = {"0": {"id": 0, "params": {"gain": 0.5}}}

    def clean_seat_id(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def public(self):
        return self.data


class FakeSender:
    def __init__(self):
        self.frames = []

    def sendto(self, packet, destination):
        self.frames.append((packet, destination))

    def close(self):
        pass


def bridge_entries():
    state = FakeState()
    bridge = OSCBridge(state, lambda *_args: None, 15550, 16660, "127.0.0.1")
    bridge.sender = FakeSender()
    args = ["lfo", "sine", 0.0, 1.0, "10s", "p:0.25"]
    try:
        with mock.patch.object(bridge_module.time, "time", return_value=100.0), \
                mock.patch.object(bridge_module.time, "monotonic_ns",
                                  return_value=12_250_000_000):
            bridge.set_param(0, "gain", args)
        first = dict(bridge.automation["0"]["gain"])
        with mock.patch.object(bridge_module.time, "time", return_value=105.0), \
                mock.patch.object(bridge_module.time, "monotonic_ns",
                                  return_value=17_250_000_000):
            bridge.set_param(0, "gain", args)
        second = dict(bridge.automation["0"]["gain"])
    finally:
        bridge.close()
    return first, second


def browser_result(first, second):
    script = r"""
const fs = require("fs");
const vm = require("vm");
global.window = {};
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
const first = JSON.parse(process.argv[2]);
const second = JSON.parse(process.argv[3]);
const parsed = window.ParamSpec.parse(first.args, "f");
const atCommonTime = entry => window.ParamSpec.phaseAnchor(entry, parsed, 106000);
const a = atCommonTime(first);
const b = atCommonTime(second);
const freeArgs = ["lfo", "sine", 0, 1, "10s", "free"];
const freeParsed = window.ParamSpec.parse(freeArgs, "f");
const free = window.ParamSpec.phaseAnchor(
  {args: freeArgs, sent_at: 100, phase_at_send_ms: 9999}, freeParsed, 100000);
process.stdout.write(JSON.stringify({a, b, free}));
"""
    completed = subprocess.run(
        ["node", "-e", script,
         os.path.join(REPO, "dashboard", "static", "js", "paramspec.js"),
         json.dumps(first), json.dumps(second)],
        cwd=REPO, text=True, capture_output=True, check=False)
    if completed.returncode:
        raise RuntimeError(completed.stderr or completed.stdout)
    return json.loads(completed.stdout)


def main():
    first, second = bridge_entries()
    check("bridge records leader phase on initial non-free LFO",
          abs(first.get("phase_at_send_ms", -1) - 4750) < 0.001, repr(first))
    check("bridge samples advancing leader phase on identical retrigger",
          abs(second.get("phase_at_send_ms", -1) - 9750) < 0.001, repr(second))
    result = browser_result(first, second)
    first_elapsed = result["a"]["elapsedMs"]
    second_elapsed = result["b"]["elapsedMs"]
    check("browser resolves both sends to the same phase at a common time",
          abs((first_elapsed - second_elapsed) % 10000) < 0.001, repr(result))
    check("free LFO keeps its independent deterministic visual phase",
          0 <= result["free"]["elapsedMs"] < 10000
          and abs(result["free"]["elapsedMs"] - 9999) > 1, repr(result))
    print(f"\n{4 - len(FAILURES)}/4 passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
