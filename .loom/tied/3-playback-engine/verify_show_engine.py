#!/usr/bin/env python3
"""Verification for 14-show-tab stitch 3 (playback engine).

A real `dashboard/server.py` + `tools/simfleet.py` (one simulated device) on
non-default ports, driven entirely over a real websocket connection --
building one show document through the stitch-2 WS edit surface, then
exercising the stitch-3 transport surface (`step_start`/`step_stop`/
`step_pause`/`step_resume`/`step_trigger_next`/`stop_all_steps`) and
asserting on:

  - OSC actually observed by simfleet's stdout log (`p/<name>=<value>` for
    `/p/*` messages, `cue-recv .../fire_mono=` for `/cue`), which carries
    monotonic-nanosecond precision for the fire instant even though the log
    line's leading wall-clock stamp is only second-resolution.
  - `show_playback` WS broadcasts (full snapshot on connect and after every
    transport-driven change, per the design note sec 3).

All step durations are kept sub-second so the whole run finishes quickly.
Run:  ~/.venvs/bopos/bin/python verify_show_engine.py
Deps: fastapi, uvicorn[standard], websockets (dashboard/requirements.txt).
"""

import asyncio
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

import websockets

sys.dont_write_bytecode = True

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    with socket.socket(socket.AF_INET, kind) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


# --------------------------------------------------------------------------
# WS helpers (pattern from verify_show_model.py)
# --------------------------------------------------------------------------

async def drain_connect_messages(ws, wanted, timeout=5.0):
    collected = {}
    deadline = asyncio.get_event_loop().time() + timeout
    while not set(wanted) <= set(collected):
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        message = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        collected[message["type"]] = message["data"]
    return collected


async def send_and_wait(ws, kind, data, wanted_types, timeout=5.0):
    await ws.send(json.dumps({"type": kind, "data": data}))
    collected = {}
    deadline = asyncio.get_event_loop().time() + timeout
    while not set(wanted_types) <= set(collected):
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        message = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        collected.setdefault(message["type"], []).append(message["data"])
    return collected


async def add_step(ws, after_uid=None):
    result = await send_and_wait(ws, "add_step", {"after_uid": after_uid}, {"show"})
    doc = result["show"][-1]
    return doc["items"][-1]["uid"]


async def add_divider(ws, after_uid=None):
    result = await send_and_wait(ws, "add_divider", {"after_uid": after_uid}, {"show"})
    doc = result["show"][-1]
    return doc["items"][-1]["uid"]


async def add_message(ws, step_uid, address, args, target="all"):
    message = {"address": address, "args": args, "target": target}
    result = await send_and_wait(
        ws, "add_message", {"step_uid": step_uid, "message": message}, {"show"})
    doc = result["show"][-1]


async def update_step(ws, uid, **patch):
    await send_and_wait(ws, "update_step", {"uid": uid, **patch}, {"show"})


async def send(ws, kind, data):
    await ws.send(json.dumps({"type": kind, "data": data}))


async def settle(ws, seconds):
    """Drain every broadcast that arrives within `seconds`, keeping only the
    most recent payload per message type.

    Timer-driven transitions (duration expiry, play-n-times re-emission,
    then-action resolution) can each fire their own `show_playback`
    broadcast while nothing reads the socket (e.g. during a bare
    `asyncio.sleep`); a plain "read one message and stop" helper then risks
    handing back a stale, superseded snapshot instead of the settled one.
    This is the fix: it behaves like `sleep(seconds)` but continuously
    drains the socket the whole time, so callers always see the freshest
    `show_playback` (a full-state broadcast, so the latest one is always a
    complete picture) once the window elapses.
    """
    latest = {}
    deadline = asyncio.get_event_loop().time() + seconds
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            return latest
        try:
            message = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        except asyncio.TimeoutError:
            return latest
        latest[message["type"]] = message["data"]


def farg(value):
    return {"type": "f", "value": value}


def sarg(value):
    return {"type": "s", "value": value}


# --------------------------------------------------------------------------
# Server + simfleet harness
# --------------------------------------------------------------------------

def start_server(http_port, report_port, cmd_port, state_file):
    return subprocess.Popen([
        sys.executable, os.path.join(REPO, "dashboard", "server.py"),
        "--port", str(http_port), "--listen-port", str(report_port),
        "--send-port", str(cmd_port), "--osc-target", "127.0.0.1",
        "--state-file", state_file,
    ], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def start_fleet(report_port, cmd_port, state_dir):
    return subprocess.Popen([
        sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
        "--devices", "1", "--target", "127.0.0.1",
        "--report-port", str(report_port), "--cmd-port", str(cmd_port),
        "--hb-interval", "0.3", "--boot-secs", "0.2",
        "--state-dir", state_dir,
    ], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


async def pump_lines(proc, buffer):
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, proc.stdout.readline)
        if not line:
            return
        buffer.append(line.rstrip("\n"))


async def wait_http(url, attempts=60):
    import urllib.request
    for _ in range(attempts):
        try:
            urllib.request.urlopen(url, timeout=0.5).close()
            return True
        except Exception:
            await asyncio.sleep(0.25)
    return False


def matches(buffer, start, pattern):
    regex = re.compile(pattern)
    return [line for line in buffer[start:] if regex.search(line)]


def fire_mono_of(line):
    match = re.search(r"fire_mono=(\d+)", line)
    return int(match.group(1)) if match else None


async def run():
    http_port = free_port(socket.SOCK_STREAM)
    report_port = free_port(socket.SOCK_DGRAM)
    cmd_port = free_port(socket.SOCK_DGRAM)
    root = tempfile.mkdtemp(prefix="bopos-show-engine-")
    state_file = os.path.join(root, "installation.json")
    fleet_state = os.path.join(root, "fleet")
    os.makedirs(fleet_state, exist_ok=True)

    server = start_server(http_port, report_port, cmd_port, state_file)
    fleet = start_fleet(report_port, cmd_port, fleet_state)
    fleet_log = []
    fleet_pump = asyncio.create_task(pump_lines(fleet, fleet_log))
    ws = None
    extra_ws = []
    try:
        check("server http responds",
              await wait_http(f"http://127.0.0.1:{http_port}/"))

        ws = await websockets.connect(f"ws://127.0.0.1:{http_port}/ws")
        connect = await drain_connect_messages(
            ws, {"state", "distribution", "venues", "shows", "show", "show_playback"})
        check("show_playback sent on connect", connect.get("show_playback") == {"steps": {}},
              repr(connect.get("show_playback")))

        # Let the one simulated device boot so /cue reaches a "running" node
        # (handle_cue in simfleet fires per-device regardless of assignment,
        # but only once state != "booting").
        await settle(ws, 0.5)

        # ------------------------------------------------------------
        # Build one show document through the stitch-2 WS edit surface.
        # ------------------------------------------------------------
        await send_and_wait(ws, "create_show", {"name": "verify-engine"}, {"show", "shows"})

        msg_uid = await add_step(ws)
        await add_message(ws, msg_uid, "/p/gain", [farg(0.11)])
        await add_message(ws, msg_uid, "/p/gain2", [farg(0.22)])
        await update_step(ws, msg_uid, duration_s=0.05, play_count=1, then_actions=[])

        loop_uid = await add_step(ws, msg_uid)
        await add_message(ws, loop_uid, "/p/backing", [farg(0.5)])
        await update_step(ws, loop_uid, duration_s=0.05, play_count=3, then_actions=[])

        divider_uid = await add_divider(ws, loop_uid)
        a_uid = await add_step(ws, divider_uid)
        await add_message(ws, a_uid, "/p/gain", [farg(0.31)])
        b_uid = await add_step(ws, a_uid)
        await add_message(ws, b_uid, "/p/gain2", [farg(0.32)])
        c_uid = await add_step(ws, b_uid)
        await add_message(ws, c_uid, "/p/backing", [farg(0.33)])
        await update_step(ws, a_uid, duration_s=0.05, play_count=1,
                          then_actions=[{"type": "next_step"}])
        await update_step(ws, b_uid, duration_s=0.05, play_count=1,
                          then_actions=[{"type": "goto", "target_uid": c_uid}])
        await update_step(ws, c_uid, duration_s=0.05, play_count=1, then_actions=[])

        divider_uid = await add_divider(ws, c_uid)
        x_uid = await add_step(ws, divider_uid)
        await add_message(ws, x_uid, "/p/gain", [farg(0.41)])
        y_uid = await add_step(ws, x_uid)
        await add_message(ws, y_uid, "/p/gain", [farg(0.42)])
        z_uid = await add_step(ws, y_uid)
        await add_message(ws, z_uid, "/p/gain", [farg(0.43)])
        for uid in (x_uid, y_uid, z_uid):
            await update_step(ws, uid, duration_s=0.03, play_count=1,
                              then_actions=[{"type": "other_in_section"}])

        divider_uid = await add_divider(ws, z_uid)
        x2_uid = await add_step(ws, divider_uid)
        await add_message(ws, x2_uid, "/p/gain", [farg(0.51)])
        y2_uid = await add_step(ws, x2_uid)
        await add_message(ws, y2_uid, "/p/gain", [farg(0.52)])
        for uid in (x2_uid, y2_uid):
            await update_step(ws, uid, duration_s=0.03, play_count=1,
                              then_actions=[{"type": "any_in_section"}])

        divider_uid = await add_divider(ws, y2_uid)
        p_uid = await add_step(ws, divider_uid)
        await add_message(ws, p_uid, "/p/gain", [farg(0.71)])
        await update_step(ws, p_uid, duration_s=0.05, play_count=1, then_actions=[])
        q_uid = await add_step(ws, p_uid)
        await add_message(ws, q_uid, "/p/gain", [farg(0.72)])
        await update_step(ws, q_uid, duration_s=0.05, play_count=1, then_actions=[])
        multi_uid = await add_step(ws, q_uid)
        await add_message(ws, multi_uid, "/p/gain", [farg(0.60)])
        await update_step(ws, multi_uid, duration_s=0.05, play_count=1, then_actions=[
            {"type": "goto", "target_uid": p_uid}, {"type": "goto", "target_uid": q_uid}])

        divider_uid = await add_divider(ws, multi_uid)
        pause_uid = await add_step(ws, divider_uid)
        await add_message(ws, pause_uid, "/p/gain", [farg(0.81)])
        await update_step(ws, pause_uid, duration_s=0.5, play_count=1, then_actions=[])

        divider_uid = await add_divider(ws, pause_uid)
        stopa_uid = await add_step(ws, divider_uid)
        await add_message(ws, stopa_uid, "/p/gain", [farg(0.91)])
        await update_step(ws, stopa_uid, duration_s=2.0, play_count=1, then_actions=[])
        stopb_uid = await add_step(ws, stopa_uid)
        await add_message(ws, stopb_uid, "/p/gain", [farg(0.92)])
        await update_step(ws, stopb_uid, duration_s=2.0, play_count=1, then_actions=[])

        divider_uid = await add_divider(ws, stopb_uid)
        cue_sync_uid = await add_step(ws, divider_uid)
        await add_message(ws, cue_sync_uid, "/cue", [sarg("cueA")])
        await update_step(ws, cue_sync_uid, duration_s=0.05, play_count=1,
                          then_actions=[], forward_sync=True)
        cue_now_uid = await add_step(ws, cue_sync_uid)
        await add_message(ws, cue_now_uid, "/cue", [sarg("cueB")])
        await update_step(ws, cue_now_uid, duration_s=0.05, play_count=1,
                          then_actions=[], forward_sync=False)

        # ------------------------------------------------------------
        # Test 1: a step fires its whole message set together.
        # ------------------------------------------------------------
        mark = len(fleet_log)
        await send(ws, "step_start", {"uid": msg_uid})
        await settle(ws, 0.15)
        check("message set: gain fired", matches(fleet_log, mark, r"p/gain=0\.11"))
        check("message set: gain2 fired", matches(fleet_log, mark, r"p/gain2=0\.22"))
        await send(ws, "stop_all_steps", {})
        await settle(ws, 0.1)

        # ------------------------------------------------------------
        # Test 2: play-n-times loops n emissions then resolves.
        # ------------------------------------------------------------
        mark = len(fleet_log)
        await send(ws, "step_start", {"uid": loop_uid})
        latest = await settle(ws, 0.5)
        hits = matches(fleet_log, mark, r"p/backing=0\.5\b")
        check("play-n-times: exactly 3 emissions", len(hits) == 3, repr(hits))
        check("play-n-times: settled stopped",
              loop_uid not in latest.get("show_playback", {}).get("steps", {}),
              repr(latest.get("show_playback")))
        await send(ws, "stop_all_steps", {})
        await settle(ws, 0.1)

        # ------------------------------------------------------------
        # Test 3: next_step / goto chain walks correctly.
        # ------------------------------------------------------------
        mark = len(fleet_log)
        await send(ws, "step_start", {"uid": a_uid})
        latest = await settle(ws, 0.5)
        seq = [line for line in fleet_log[mark:]
              if re.search(r"p/(gain=0\.31|gain2=0\.32|backing=0\.33)\b", line)]
        values = [re.search(r"p/\w+=([0-9.]+)", line).group(1) for line in seq]
        check("chain: A -> B -> C order", values == ["0.31", "0.32", "0.33"], repr(values))
        check("chain: settled stopped", latest.get("show_playback", {}).get("steps") == {},
              repr(latest.get("show_playback")))
        await send(ws, "stop_all_steps", {})
        await settle(ws, 0.1)

        # ------------------------------------------------------------
        # Test 4: other_in_section exhausts the section before repeating.
        # ------------------------------------------------------------
        mark = len(fleet_log)
        await send(ws, "step_start", {"uid": x_uid})
        await settle(ws, 0.30)
        await send(ws, "stop_all_steps", {})
        await settle(ws, 0.1)
        hits = matches(fleet_log, mark, r"p/gain=0\.4[123]\b")
        values = [re.search(r"0\.4[123]", line).group(0) for line in hits]
        check("other_in_section: several hops observed", len(values) >= 3, repr(values))
        no_immediate_repeat = all(values[i] != values[i + 1] for i in range(len(values) - 1))
        check("other_in_section: never repeats itself immediately", no_immediate_repeat,
              repr(values))
        # values[0] is X's own initial fire (from step_start), not a hop
        # pick -- the first two *hops* are values[1:3].
        first_two_hops = set(values[1:3])
        check("other_in_section: exhausts the other two before any repeat",
              first_two_hops == {"0.42", "0.43"}, repr(values))

        # ------------------------------------------------------------
        # Test 5: any_in_section stays within the section (statistical).
        # ------------------------------------------------------------
        mark = len(fleet_log)
        await send(ws, "step_start", {"uid": x2_uid})
        await settle(ws, 0.40)
        await send(ws, "stop_all_steps", {})
        await settle(ws, 0.1)
        hits = matches(fleet_log, mark, r"p/gain=0\.5[12]\b")
        values = {re.search(r"0\.5[12]", line).group(0) for line in hits}
        check("any_in_section: only in-section values observed",
              values <= {"0.51", "0.52"}, repr(values))
        check("any_in_section: both steps eventually chosen",
              values == {"0.51", "0.52"}, repr(values))

        # ------------------------------------------------------------
        # Test 6: multi-then uniform pick (statistical over repeated triggers).
        # ------------------------------------------------------------
        seen = set()
        for _ in range(20):
            mark = len(fleet_log)
            await send(ws, "step_start", {"uid": multi_uid})
            await settle(ws, 0.20)
            hits = matches(fleet_log, mark, r"p/gain=0\.7[12]\b")
            if hits:
                seen.add(re.search(r"0\.7[12]", hits[0]).group(0))
            await send(ws, "stop_all_steps", {})
            await settle(ws, 0.05)
            if seen == {"0.71", "0.72"}:
                break
        check("multi-then: both then_actions eventually picked", seen == {"0.71", "0.72"},
              repr(seen))

        # ------------------------------------------------------------
        # Test 7: pause freezes the countdown; resume continues it.
        # ------------------------------------------------------------
        mark = len(fleet_log)
        await send(ws, "step_start", {"uid": pause_uid})
        latest = await settle(ws, 0.05)
        snap = latest.get("show_playback", {}).get("steps", {}).get(pause_uid)
        check("pause: started playing", snap is not None and snap["state"] == "playing",
              repr(snap))
        await settle(ws, 0.15)
        await send(ws, "step_pause", {"uid": pause_uid})
        latest = await settle(ws, 0.1)
        paused_snap = latest.get("show_playback", {}).get("steps", {}).get(pause_uid)
        check("pause: now paused", paused_snap is not None
              and paused_snap["state"] == "paused", repr(paused_snap))
        frozen_remaining = paused_snap["remaining_s"]
        check("pause: plausible remaining time", 0.2 < frozen_remaining < 0.4,
              repr(frozen_remaining))
        await settle(ws, 0.3)  # while paused -- must not expire or decay
        ws2 = await websockets.connect(f"ws://127.0.0.1:{http_port}/ws")
        extra_ws.append(ws2)
        connect2 = await drain_connect_messages(ws2, {"show_playback"})
        still_paused = connect2["show_playback"]["steps"][pause_uid]
        check("pause: remaining time frozen while paused",
              abs(still_paused["remaining_s"] - frozen_remaining) < 0.05,
              repr((still_paused["remaining_s"], frozen_remaining)))
        check("pause: no message re-fired while paused",
              matches(fleet_log, mark, r"p/gain=0\.81\b").__len__() == 1)
        await send(ws, "step_resume", {"uid": pause_uid})
        latest = await settle(ws, frozen_remaining + 0.3)
        hits = matches(fleet_log, mark, r"p/gain=0\.81\b")
        check("resume: step expired once resumed, no re-emission", len(hits) == 1, repr(hits))
        check("resume: settled stopped after resume",
              pause_uid not in latest.get("show_playback", {}).get("steps", {}),
              repr(latest.get("show_playback")))

        # ------------------------------------------------------------
        # Test 8: stop_all_steps stops everything.
        # ------------------------------------------------------------
        await send(ws, "step_start", {"uid": stopa_uid})
        await settle(ws, 0.05)
        await send(ws, "step_start", {"uid": stopb_uid})
        latest = await settle(ws, 0.05)
        snap = latest.get("show_playback", {}).get("steps", {})
        check("stop_all: both playing before stop",
              snap.get(stopa_uid, {}).get("state") == "playing"
              and snap.get(stopb_uid, {}).get("state") == "playing", repr(snap))
        await send(ws, "stop_all_steps", {})
        latest = await settle(ws, 0.1)
        check("stop_all: snapshot empty after stop",
              latest.get("show_playback", {}).get("steps") == {},
              repr(latest.get("show_playback")))

        # ------------------------------------------------------------
        # Test 9: forward-synced /cue via the scheduled path; a non-synced
        # /cue via the immediate path. Also assert the wire type of
        # sharedTimeNs is a string (PD float precision law, sec 12).
        # ------------------------------------------------------------
        mark = len(fleet_log)
        t0 = time.monotonic_ns()
        await send(ws, "step_start", {"uid": cue_sync_uid})
        await settle(ws, 0.9)
        recv = matches(fleet_log, mark, r"cue-recv id=cueA")
        check("forward-sync: cue receipt carries a string sharedTimeNs",
              bool(recv) and "shared_time_ns_type=str" in recv[0], repr(recv))
        fired = matches(fleet_log, mark, r"cue cueA fired")
        check("forward-sync: cue fired", bool(fired), repr(fired))
        if fired:
            delay = (fire_mono_of(fired[0]) - t0) / 1e9
            check("forward-sync: fired via the ~500ms scheduled lead path",
                  0.35 <= delay <= 0.9, repr(delay))
        await send(ws, "stop_all_steps", {})
        await settle(ws, 0.1)

        mark = len(fleet_log)
        t0 = time.monotonic_ns()
        await send(ws, "step_start", {"uid": cue_now_uid})
        await settle(ws, 0.3)
        recv = matches(fleet_log, mark, r"cue-recv id=cueB")
        check("non-synced: cue receipt carries a string sharedTimeNs",
              bool(recv) and "shared_time_ns_type=str" in recv[0], repr(recv))
        fired = matches(fleet_log, mark, r"cue cueB fired")
        check("non-synced: cue fired", bool(fired), repr(fired))
        if fired:
            delay = (fire_mono_of(fired[0]) - t0) / 1e9
            check("non-synced: fired via the immediate path (well under the 500ms lead)",
                  delay < 0.2, repr(delay))
        await send(ws, "stop_all_steps", {})
        await settle(ws, 0.1)

        # ------------------------------------------------------------
        # Test 10: remove_item stops a playing step first.
        # ------------------------------------------------------------
        await send(ws, "step_start", {"uid": stopa_uid})
        await settle(ws, 0.05)
        await send(ws, "remove_item", {"uid": stopa_uid})
        latest = await settle(ws, 0.2)
        check("remove_item: playing step stopped before removal",
              stopa_uid not in latest.get("show_playback", {}).get("steps", {}),
              repr(latest.get("show_playback")))
        check("remove_item: item actually removed",
              "show" in latest
              and all(item["uid"] != stopa_uid for item in latest["show"]["items"]),
              repr(latest.get("show")))

    finally:
        for extra in extra_ws:
            await extra.close()
        if ws is not None:
            await ws.close()
        fleet_pump.cancel()
        for proc in (fleet, server):
            proc.terminate()
        for proc in (fleet, server):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        server_out = server.stdout.read() if server.stdout else ""
        check("server produced no traceback", "Traceback" not in server_out, server_out[-4000:])
        import shutil
        shutil.rmtree(root, ignore_errors=True)


def main():
    asyncio.run(run())
    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed:")
        for label in FAILURES:
            print(f"  - {label}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
