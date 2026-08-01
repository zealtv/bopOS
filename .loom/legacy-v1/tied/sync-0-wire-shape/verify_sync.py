#!/usr/bin/env python3
"""Wire-shape verification for sync-0: /sync/ping-pong, /sync/offset, /cue.

Drives tools/simfleet.py (protocol v1) as the clock leader over UDP on
non-default ports -- no browser, the sync plane is LAN/engine only. Because
leader and sim share Linux's system-wide CLOCK_MONOTONIC, a correct pushed
offset cancels each device's fake skew and all devices fire one /cue at the
same real instant.

Checks:
  1. /sync/pong is well-formed: seq + leaderTime echoed, uid == a device mac,
     deviceTime parses as an int nanosecond count.
  2. a /cue sent 1.5 s ahead fires on every device within tolerance of each
     other AND of the intended instant, after /<id>/sync/offset is pushed
     (skew cancelled -- the whole point of clock sync).

Deps: pip install python-osc. Run:  python3 verify_sync.py
"""
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

from pythonosc import osc_message, osc_message_builder

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent

REPORT_PORT = 15571   # leader listens here (fleet -> leader): pongs + heartbeats
CMD_PORT = 16681      # fleet listens here (leader -> fleet): ping, offset, cue
SKEW_MS = 40.0        # per-device fake clock skew spread
JITTER_MS = 1.0       # per-pong measurement noise
FUTURE_NS = 1_500_000_000   # schedule the cue 1.5 s ahead
COHERENCE_NS = 20_000_000   # devices must fire within 20 ms of each other
ACCURACY_NS = 25_000_000    # ...and within 25 ms of the intended instant

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def build(address, *typed):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value, kind in typed:
        builder.add_arg(value, arg_type=kind)
    return builder.build().dgram


def drain(sock, seconds):
    """Collect (address, args, recv_ns) for `seconds`. recv_ns is the leader's
    monotonic clock when the packet arrived -- needed for honest offset math
    (computing it after the loop would fold in the whole drain window)."""
    messages = []
    deadline = time.monotonic() + seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return messages
        sock.settimeout(remaining)
        try:
            datagram, _ = sock.recvfrom(65535)
        except socket.timeout:
            return messages
        recv_ns = time.monotonic_ns()
        try:
            message = osc_message.OscMessage(datagram)
        except Exception:
            continue
        messages.append((message.address, list(message.params), recv_ns))


def main():
    leader = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    leader.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    leader.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    leader.bind(("", REPORT_PORT))
    fleet_addr = ("127.0.0.1", CMD_PORT)

    log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    fleet = subprocess.Popen([
        sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "2",
        "--protocol", "v1", "--target", "127.0.0.1",
        "--report-port", str(REPORT_PORT), "--cmd-port", str(CMD_PORT),
        "--hb-interval", "1.0", "--boot-secs", "1.0", "--meter-interval", "0",
        "--sync-skew-ms", str(SKEW_MS), "--sync-jitter-ms", str(JITTER_MS),
    ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
    try:
        time.sleep(3.0)  # let devices boot to running and start heartbeating

        # learn mac -> id from heartbeats (the leader's real source of truth)
        mac_to_id = {}
        for address, args, _recv in drain(leader, 1.5):
            if address == "/hb" and len(args) >= 2:
                mac_to_id[str(args[0])] = int(args[1])
        check("heartbeats seen from both devices", len(mac_to_id) == 2,
              f"macs={mac_to_id}")

        # 1. ping -> well-formed pong
        seq = 7
        send_ns = time.monotonic_ns()
        leader.sendto(build("/sync/ping", (seq, "i"), (str(send_ns), "s")), fleet_addr)
        leader_time = str(send_ns)
        pongs = [(args, recv) for a, args, recv in drain(leader, 1.0)
                 if a == "/sync/pong"]
        check("a pong per device", len(pongs) >= 2, f"got {len(pongs)}")

        offsets = {}  # id -> offsetNs
        well_formed = True
        for args, recv_ns in pongs:
            ok = (len(args) == 4 and int(args[0]) == seq
                  and str(args[1]) == leader_time
                  and str(args[2]) in mac_to_id
                  and re.fullmatch(r"-?\d+", str(args[3])))
            well_formed = well_formed and bool(ok)
            if ok:
                device_time = int(args[3])
                one_way = (recv_ns - send_ns) // 2
                offset = (device_time + one_way) - recv_ns
                offsets[mac_to_id[str(args[2])]] = offset
        check("pongs well-formed (seq+leaderTime echoed, uid=mac, ns int)",
              well_formed and len(offsets) == 2, f"offsets={offsets}")

        # 2. push each computed offset, then one broadcast cue 1.5 s ahead
        for device_id, offset in offsets.items():
            leader.sendto(build(f"/{device_id}/sync/offset", (str(offset), "s")),
                          fleet_addr)
        time.sleep(0.3)  # offsets applied before the cue

        shared = time.monotonic_ns() + FUTURE_NS
        leader.sendto(build("/cue", ("test1", "s"), (str(shared), "s")), fleet_addr)
        time.sleep(2.0)  # let the deadline pass and fires log

        fleet.terminate()
        fleet.wait(timeout=5)
        log.flush()
        fires = {}
        with open(log.name) as source:
            for line in source:
                m = re.search(r"id=(\S+).*cue test1 fired .*fire_mono=(\d+)", line)
                if m:
                    fires[m.group(1)] = int(m.group(2))
        check("cue fired on both devices", len(fires) == 2, f"fires={fires}")
        if len(fires) == 2:
            values = list(fires.values())
            spread = abs(values[0] - values[1])
            worst = max(abs(v - shared) for v in values)
            check("devices fired coherently (skew cancelled)", spread <= COHERENCE_NS,
                  f"spread={spread/1e6:.1f}ms > {COHERENCE_NS/1e6:.0f}ms")
            check("fired at the intended instant", worst <= ACCURACY_NS,
                  f"worst={worst/1e6:.1f}ms > {ACCURACY_NS/1e6:.0f}ms")
    finally:
        if fleet.poll() is None:
            fleet.terminate()
            fleet.wait(timeout=5)
        leader.close()
        try:
            os.unlink(log.name)
        except OSError:
            pass

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("sync-0 wire-shape checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
