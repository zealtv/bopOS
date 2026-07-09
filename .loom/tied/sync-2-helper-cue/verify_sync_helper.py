#!/usr/bin/env python3
"""Verification for sync-2: the node side (helper.py + sync_node.py).

Two parts, both browser- and hardware-free:

  A. sync_node unit checks (deterministic where it can be): SyncState slews a
     pushed offset in rather than stepping and stays continuous across a second
     push; CueScheduler fires at sharedTime+offset, honours the late-grace, and
     drops a stale cue.
  B. loopback integration against the REAL helper.py LAN handler: import
     helper.py (binds 7770 harmlessly in this test process), drive
     handle_lan_datagram directly -- a /sync/ping gets a well-formed /sync/pong,
     a /<id>/sync/offset is applied, and a /cue scheduled 400 ms out fires the
     bare /cue to the engine socket (6661) within a loopback-tight bound.

Real-hardware sync (PD firing, GPIO-measured jitter) belongs to sync-4/sync-3,
not here. Deps: pip install pyOSC3. Run: python3 verify_sync_helper.py
"""
import os
import socket
import sys
import time

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "python"))

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def unit_checks():
    import sync_node

    # --- SyncState slew (injected logical clock: fully deterministic) ---
    clock = {"ns": 0}
    state = sync_node.SyncState(slew_ns=1_000_000_000, now=lambda: clock["ns"])
    check("offset is 0 before any push", state.offset() == 0 and not state.synced())
    state.push(1_000_000)  # target 1 ms
    check("push does not step (starts near old value)", abs(state.offset()) < 50_000)
    clock["ns"] = 500_000_000  # half the slew window
    check("slews ~halfway", abs(state.offset() - 500_000) < 60_000,
          f"offset={state.offset()}")
    clock["ns"] = 1_000_000_000
    check("reaches target after the slew window", state.offset() == 1_000_000)
    # a second push mid-way stays continuous (no jump) then converges
    clock["ns"] = 1_000_000_000
    state.push(-1_000_000)
    check("second push is continuous", abs(state.offset() - 1_000_000) < 50_000,
          f"offset={state.offset()}")
    clock["ns"] = 2_000_000_000
    check("converges to the new target", state.offset() == -1_000_000)

    # --- CueScheduler (real clock, real thread, generous bounds) ---
    fired, logs = [], []
    live = sync_node.SyncState(slew_ns=0)  # step (no slew) so offset is exact
    live.push(0)
    scheduler = sync_node.CueScheduler(
        live, fire=lambda cid: fired.append((cid, time.monotonic_ns())),
        log=logs.append)
    scheduler.start()
    try:
        shared = time.monotonic_ns() + 150_000_000  # 150 ms out
        scheduler.schedule(shared, "ontime")
        scheduler.schedule(time.monotonic_ns() - 10_000_000, "grace")   # 10 ms late
        scheduler.schedule(time.monotonic_ns() - 300_000_000, "stale")  # 300 ms late
        time.sleep(0.4)
        names = [cid for cid, _ in fired]
        check("on-time cue fired", "ontime" in names)
        check("within-grace late cue fired", "grace" in names)
        check("stale cue dropped, not fired", "stale" not in names)
        check("dropped cue is logged", any("stale" in line and "DROPPED" in line
                                            for line in logs))
        when = dict(fired).get("ontime")
        check("on-time cue fired near its deadline",
              when is not None and abs(when - shared) < 40_000_000,
              f"delta={(when - shared)/1e6:.1f}ms" if when else "not fired")
    finally:
        scheduler.stop()


def integration_checks():
    from pyOSC3 import OSCMessage, decodeOSC
    import helper

    helper.node_state.id = 1
    helper.node_state.uid = "testuid00"
    engine = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    engine.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    engine.bind(("127.0.0.1", 6661))   # catch the bare /cue helper fires to PD
    engine.settimeout(1.5)
    leader = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    leader.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    leader.bind(("127.0.0.1", 5550))   # receive the pong (helper replies here)
    leader.settimeout(1.5)
    source = ("127.0.0.1", 5550)
    helper.cue_scheduler.start()
    try:
        # ping -> pong
        seq, leader_time = 5, str(time.monotonic_ns())
        ping = OSCMessage("/sync/ping")
        ping.append(seq, 'i')
        ping.append(leader_time, 's')
        helper.handle_lan_datagram(ping.getBinary(), source, leader, helper.node_state)
        pong = decodeOSC(leader.recvfrom(65535)[0])
        args = pong[2:]
        check("pong address + shape", str(pong[0]) == "/sync/pong" and len(args) == 4,
              f"{pong}")
        check("pong echoes seq + leaderTime, carries uid + int deviceTime",
              int(args[0]) == seq and str(args[1]) == leader_time
              and str(args[2]) == "testuid00" and str(int(args[3])) == str(args[3]),
              f"args={args}")

        # /<id>/sync/offset applied (0 for loopback)
        off = OSCMessage("/1/sync/offset")
        off.append(str(0), 's')
        helper.handle_lan_datagram(off.getBinary(), source, leader, helper.node_state)
        check("offset applied", helper.sync_state.synced()
              and abs(helper.sync_state.offset()) < 1_000_000)

        # /cue 400 ms out -> bare /cue fired to the engine at the deadline
        shared = time.monotonic_ns() + 400_000_000
        cue = OSCMessage("/cue")
        cue.append("c1", 's')
        cue.append(str(shared), 's')
        helper.handle_lan_datagram(cue.getBinary(), source, leader, helper.node_state)
        datagram, _ = engine.recvfrom(65535)
        arrival = time.monotonic_ns()
        fired = decodeOSC(datagram)
        check("engine got the bare cue", str(fired[0]) == "/cue"
              and str(fired[2]) == "c1", f"{fired}")
        check("cue fired near its deadline (offset 0 -> deadline = sharedTime)",
              abs(arrival - shared) < 60_000_000,
              f"delta={(arrival - shared)/1e6:.1f}ms")
    finally:
        helper.cue_scheduler.stop()
        engine.close()
        leader.close()


def main():
    print("-- sync_node unit checks --")
    unit_checks()
    print("-- helper.py loopback integration --")
    integration_checks()
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("sync-2 helper/cue checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
