#!/usr/bin/env python3
"""Bounded reproductions for the show-model review (74/4).

Run from the repository root:

    PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
        .loom/threads/74-review-remaining/4-review-show-model.stitching/reproduce.py

Opens no sockets and starts no engines. Fixtures live in one /tmp temporary
directory. Engine runs use a recording fake bridge and stop within ~0.5 s.
Each case asserts the observed defect; a passing run means every defect is
still present.
"""

import asyncio
import json
import os
import sys
import tempfile
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))
sys.path.insert(0, os.path.join(REPO, "dashboard"))
sys.path.insert(0, REPO)

import show_model  # noqa: E402
from show_engine import ShowEngine  # noqa: E402
from state import InstallationState  # noqa: E402
from osc_bridge import OSCBridge  # noqa: E402

TMP = tempfile.mkdtemp(prefix="bopos-74-4-", dir="/tmp")


def step(uid, messages=(), duration_s=1.0, play_count=1, then=None):
    return {"kind": "step", "uid": uid, "alias": None, "messages": list(messages),
            "duration_s": duration_s, "play_count": play_count,
            "then_actions": then or [{"type": "stop"}]}


def message(uid, args, address="/x"):
    return {"kind": "osc", "uid": uid, "alias": None, "address": address,
            "args": args, "target": ["all"]}


def raises(fn, *args):
    try:
        fn(*args)
    except Exception as error:  # noqa: BLE001 -- the type is the finding
        return type(error).__name__
    return None


class FakeBridge:
    def __init__(self, build=False):
        self.sent, self.build = [], build

    def send(self, address, args):
        if self.build:  # the real datagram builder, no socket
            OSCBridge._datagram(address, args)
        self.sent.append((address, list(args)))

    def set_param(self, selector, name, value):
        self.send(f"/{selector}/p/{name}", value)

    def fire_event(self, selector, identity, args, lead_ms=500):
        self.send(f"/{selector}/e/{identity}", args)


async def no_broadcast(_type, _data):
    pass


def f1():
    """Out-of-range numbers in a show file crash load_show and state.public."""
    bodies = {
        "int_inf": '{"type": "i", "value": 1e999}',
        "float_bigint": '{"type": "f", "value": ' + "9" * 400 + "}",
    }
    for label, arg in bodies.items():
        path = os.path.join(TMP, f"{label}.json")
        with open(path, "w") as target:
            target.write('{"schema": 1, "name": "x", "items": [{"kind": "step",'
                         ' "uid": "aaaaaaaa", "duration_s": 1, "play_count": 1,'
                         ' "messages": [{"uid": "bbbbbbbb", "address": "/x",'
                         ' "target": "all", "args": [' + arg + ']}]}]}')
        error = raises(show_model.load_show, path)
        assert error == "OverflowError", (label, error)
        print(f"F1 load_show({label}) raises {error} (only ValueError is caught)")
    path = os.path.join(TMP, "duration.json")
    with open(path, "w") as target:
        target.write('{"schema": 1, "items": [{"kind": "step", "uid": "aaaaaaaa",'
                     ' "duration_s": ' + "9" * 400 + ', "play_count": 1}]}')
    error = raises(show_model.load_show, path)
    assert error == "OverflowError", error
    print(f"F1 load_show(duration_s=400-digit int) raises {error}")

    # The project menu loads every show on every state snapshot.
    stub = type("Stub", (), {})()
    stub.list_shows = lambda: ["int_inf"]
    stub.show_file = lambda name: os.path.join(TMP, name + ".json")
    error = raises(InstallationState.show_step_counts, stub)
    assert error == "OverflowError", error
    print(f"F1 InstallationState.show_step_counts with that file raises {error}")


def f2():
    """WS edit payloads raise instead of returning an edit error."""
    show = {"schema": 1, "name": "x", "items": [step("aaaaaaaa")]}
    error = raises(show_model.update_step, show, "aaaaaaaa", {"duration_s": 10 ** 400})
    assert error == "OverflowError", error
    print(f"F2 update_step(duration_s=10**400) raises {error}")
    error = raises(show_model.add_message, show, "aaaaaaaa",
                   {"address": "/x", "target": "all",
                    "args": [{"type": "i", "value": float("inf")}]})
    assert error == "OverflowError", error
    print(f"F2 add_message(i=Infinity) raises {error}")


def f3():
    """Int args are coerced or accepted beyond int32; the wire changes type."""
    cases = [({"type": "i", "value": 1.9}, 1), ({"type": "i", "value": "12"}, 12),
             ({"type": "f", "value": "1e5"}, 100000.0),
             ({"type": "i", "value": 2 ** 31}, 2 ** 31)]
    for raw, expected in cases:
        cleaned = show_model.clean_arg(raw)
        assert cleaned is not None and cleaned["value"] == expected, (raw, cleaned)
        print(f"F3 clean_arg({raw}) -> {cleaned}")
    dgram = OSCBridge._datagram("/x", [2 ** 31])
    assert b",h" in dgram, dgram
    print("F3 2**31 is sent with OSC type tag 'h' (int64), not 'i'")
    error = raises(OSCBridge._datagram, "/x", [2 ** 64])
    assert error == "BuildError", error
    print(f"F3 2**64 is accepted by the model and raises {error} at send")


async def f4():
    """A send failure during a repeat leaves a step 'playing' with no timer."""
    good = show_model.clean_show({"schema": 1, "name": "x", "items": [
        step("aaaaaaaa", [message("bbbbbbbb", [{"type": "i", "value": 2 ** 64}])],
             duration_s=0.05, play_count=None)]})
    assert good is not None
    engine = ShowEngine(FakeBridge(build=True), no_broadcast, seed=1)
    engine.show = good
    error = None
    try:
        await engine.step_start("aaaaaaaa")
    except Exception as exc:  # noqa: BLE001
        error = type(exc).__name__
    state = engine.playback.get("aaaaaaaa")
    assert error == "BuildError" and state and state["state"] == "playing" \
        and state["timer"] is None, (error, state)
    print(f"F4 step_start raises {error}; the step stays 'playing' with no timer "
          "(show_playing() true until Stop all)")


async def f5():
    """Undo that removes a playing step leaves a ghost playback entry."""
    before = {"schema": 1, "name": "x", "items": []}
    after, added, _ = show_model.add_step(before)
    after, _, _ = show_model.update_step(after, added["uid"], {"duration_s": 0.05})
    engine = ShowEngine(FakeBridge(), no_broadcast, seed=1)
    engine.show = after
    await engine.step_start(added["uid"])
    engine.show = before  # what server.undo_show does, with no playback check
    await asyncio.sleep(0.15)
    state = engine.playback.get(added["uid"])
    assert state is not None and state["state"] == "playing", state
    snap = engine.snapshot()
    print(f"F5 after undo + expiry: playback={list(engine.playback)} "
          f"state={state['state']} remaining={snap['steps'][added['uid']]['remaining_s']}"
          " (never cleared; clear_show and show management stay refused)")


async def f6():
    """A tiny positive duration defeats the zero-duration busy-loop guard."""
    show = show_model.clean_show({"schema": 1, "name": "x", "items": [
        step("aaaaaaaa", [message("bbbbbbbb", [])], duration_s=1e-9, play_count=None)]})
    assert show is not None
    bridge = FakeBridge()
    engine = ShowEngine(bridge, no_broadcast, seed=1)
    engine.show = show
    await engine.step_start("aaaaaaaa")
    start = time.monotonic()
    await asyncio.sleep(0.25)
    await engine.stop_all_steps()
    rate = len(bridge.sent) / (time.monotonic() - start)
    assert rate > 1000, rate
    print(f"F6 duration_s=1e-9, play_count=null accepted; ~{rate:,.0f} OSC sends/s")


def f7():
    """Every state snapshot reads and validates every show file."""
    calls = []
    original = show_model.load_show

    def counting(path):
        calls.append(path)
        return original(path)

    stub = type("Stub", (), {})()
    stub.list_shows = lambda: [f"s{i}" for i in range(5)]
    stub.show_file = lambda name: os.path.join(TMP, "missing-" + name + ".json")
    show_model.load_show = counting
    try:
        for _ in range(3):  # three state broadcasts
            InstallationState.show_step_counts(stub)
    finally:
        show_model.load_show = original
    assert len(calls) == 15, calls
    print(f"F7 3 state snapshots x 5 shows -> {len(calls)} show-file loads")


def f8():
    """Show addresses accept text that is not an OSC address."""
    for address in ("/", "/a b#", "/x//y"):
        cleaned = show_model.clean_message(message("bbbbbbbb", [], address))
        assert cleaned is not None, address
    print("F8 addresses '/', '/a b#', '/x//y' are accepted")


def main():
    f1()
    f2()
    f3()
    asyncio.run(f4())
    asyncio.run(f5())
    asyncio.run(f6())
    f7()
    f8()
    print(f"all reproductions observed; fixtures in {TMP}")


if __name__ == "__main__":
    main()
