#!/usr/bin/env python3
"""Clock-sync jitter harness (clock-sync thread, sync-3).

Measures how tightly a /cue actually fires across N devices. It acts as a
minimal clock leader -- ping/pong, estimate each device's offset, push
/<id>/sync/offset (the same low-RTT-median math as the dashboard leader,
dashboard/osc_bridge.py) -- then fires a cue burst and gathers each device's
real fire timestamp, reporting the cross-device spread.

Two evidence modes:

  sim (default)  Launches tools/simfleet.py itself, syncs it, fires the burst,
                 and reads each device's `fire_mono=<ns>` line from simfleet's
                 stdout. Fully hardware-free; the spread it reports is the
                 SOFTWARE FLOOR (one process, one clock) -- a floor, not the
                 deliverable. Writes a Markdown report.

  hardware       Assumes real Pis running bopos.py are already on the LAN
                 (each toggles a GPIO / clicks at fire time for external
                 recording -- bopos.py logs `fire_mono` too, but the honest
                 cross-device evidence is the external recording). The tool
                 syncs them, prints per-device offsets, fires the burst, and
                 prints the expected fire schedule (leader clock) so a recording
                 can be aligned. Designed here; the real run is sync-4 (Bob).

Usage:
  python3 tools/sync_measure.py --devices 5 --sync-skew-ms 40 --report out.md
  python3 tools/sync_measure.py --mode hardware --cues 8   # no sim, prints plan

Deps: pip install python-osc
"""
import argparse
import os
import re
import socket
import statistics
import subprocess
import sys
import tempfile
import time

from pythonosc import osc_message, osc_message_builder

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))

# Mirrors dashboard/osc_bridge.py's estimator (kept local: this is a standalone
# measurement leader, not the production dashboard one).
SYNC_WINDOW = 16
SYNC_RTT_CEILING_NS = 200_000_000
SYNC_LOWRTT_BAND = 1.5


def build(address, *typed):
    builder = osc_message_builder.OscMessageBuilder(address=address)
    for value, kind in typed:
        builder.add_arg(value, arg_type=kind)
    return builder.build().dgram


def estimate(offsets, rtts):
    floor = min(rtts) * SYNC_LOWRTT_BAND
    best = [offset for offset, rtt in zip(offsets, rtts) if rtt <= floor]
    return int(statistics.median(best or offsets))


class Leader:
    """A minimal clock-sync leader over one UDP socket."""

    def __init__(self, report_port, cmd_port, target):
        self.cmd = ("127.0.0.1" if target in ("", "127.0.0.1") else target, cmd_port)
        self.report_port = report_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("", report_port))
        self.samples = {}     # uid -> (offsets[], rtts[])
        self.mac_to_id = {}
        self.offsets = {}     # uid -> estimated offset ns
        self._seq = 0

    def send(self, address, *typed):
        self.sock.sendto(build(address, *typed), self.cmd)

    def ping(self):
        self._seq = (self._seq + 1) & 0x7fffffff
        self.send("/sync/ping", (self._seq, "i"), (str(time.monotonic_ns()), "s"))

    def pump(self, seconds):
        """Ping, absorb pongs/heartbeats, push offsets, for `seconds`."""
        deadline = time.monotonic() + seconds
        next_ping = 0.0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now >= next_ping:
                self.ping()
                next_ping = now + 0.1  # 10 Hz -- fill the window fast for a measure run
            self.sock.settimeout(max(0.0, min(0.1, deadline - now)))
            try:
                datagram, _ = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            recv_ns = time.monotonic_ns()
            try:
                message = osc_message.OscMessage(datagram)
            except Exception:
                continue
            address, args = message.address, list(message.params)
            if address == "/hb" and len(args) >= 2:
                self.mac_to_id[str(args[0])] = int(args[1])
            elif address == "/sync/pong" and len(args) >= 4:
                self._absorb_pong(args, recv_ns)

    def _absorb_pong(self, args, recv_ns):
        try:
            send_time, uid, device_time = int(args[1]), str(args[2]), int(args[3])
        except (TypeError, ValueError):
            return
        rtt = recv_ns - send_time
        if rtt < 0 or rtt > SYNC_RTT_CEILING_NS:
            return
        offsets, rtts = self.samples.setdefault(uid, ([], []))
        offsets.append((device_time + rtt // 2) - recv_ns)
        rtts.append(rtt)
        del offsets[:-SYNC_WINDOW]
        del rtts[:-SYNC_WINDOW]
        est = estimate(offsets, rtts)
        self.offsets[uid] = est
        device_id = self.mac_to_id.get(uid)
        if device_id is not None and device_id >= 0 and len(offsets) >= 3:
            self.send(f"/{device_id}/sync/offset", (str(est), "s"))

    def fire_burst(self, count, lead_ns, gap_ns):
        """Broadcast `count` cues; returns {cueId: sharedTime_ns}."""
        base = time.monotonic_ns() + lead_ns
        schedule = {}
        for index in range(count):
            cue_id = f"m{index}"
            shared = base + index * gap_ns
            schedule[cue_id] = shared
            self.send("/cue", (cue_id, "s"), (str(shared), "s"))
        return schedule

    def close(self):
        self.sock.close()


def parse_fires(text):
    """{cueId: {device_id: fire_mono_ns}} from simfleet/helper stdout lines like
    `... id=3 ... cue m0 fired ... fire_mono=12345`."""
    fires = {}
    pattern = re.compile(r"id=(-?\d+).*?cue (\S+) (?:fired|.*fired).*?fire_mono=(\d+)")
    for line in text.splitlines():
        match = pattern.search(line)
        if match:
            device_id, cue_id, mono = int(match.group(1)), match.group(2), int(match.group(3))
            fires.setdefault(cue_id, {})[device_id] = mono
    return fires


def spread_stats(fires):
    """Per-cue cross-device spread (max - min fire_mono), in ns."""
    spreads = {}
    for cue_id, per_device in fires.items():
        if len(per_device) >= 2:
            values = list(per_device.values())
            spreads[cue_id] = max(values) - min(values)
    return spreads


def write_report(path, args, offsets, mac_to_id, schedule, fires, spreads):
    ms = lambda ns: ns / 1e6
    lines = ["# Clock-sync jitter — sim baseline", "",
             f"Generated {time.strftime('%Y-%m-%d %H:%M:%S')} by `tools/sync_measure.py`.",
             "",
             "> **Loopback / single-process floor, not the deliverable.** All sim",
             "> devices share one machine's `CLOCK_MONOTONIC` and one event loop, so",
             "> the spread below is the software floor. The real number is the",
             "> hardware run (`sync-4`): N Pis on WiFi, fire evidence recorded",
             "> externally. Target there: <10 ms typical spread.", "",
             "## Run", "",
             f"- devices: {args.devices}   skew: ±{args.sync_skew_ms} ms   "
             f"jitter: {args.sync_jitter_ms} ms   cues: {args.cues}",
             f"- sync settle: {args.settle}s   cue lead: {args.lead_ms} ms   "
             f"gap: {args.gap_ms} ms", "",
             "## Cross-device cue spread", ""]
    if spreads:
        values = list(spreads.values())
        lines += [f"- **max spread:** {ms(max(values)):.3f} ms",
                  f"- **typical (median) spread:** {ms(statistics.median(values)):.3f} ms",
                  f"- cues measured: {len(values)} / {args.cues}", "",
                  "| cue | devices | spread (ms) |", "|---|---|---|"]
        for cue_id in sorted(spreads, key=lambda c: int(c[1:]) if c[1:].isdigit() else c):
            lines.append(f"| {cue_id} | {len(fires[cue_id])} | {ms(spreads[cue_id]):.3f} |")
    else:
        lines.append("- no cue was heard on ≥2 devices (see raw output).")
    lines += ["", "## Per-device offset estimate", "",
              "| id | uid | offset (ms) |", "|---|---|---|"]
    id_to_uid = {device_id: uid for uid, device_id in mac_to_id.items()}
    for device_id in sorted(id_to_uid):
        uid = id_to_uid[device_id]
        off = offsets.get(uid)
        lines.append(f"| {device_id} | {uid} | "
                     f"{ms(off):.3f} |" if off is not None else f"| {device_id} | {uid} | — |")
    lines.append("")
    with open(path, "w") as target:
        target.write("\n".join(lines) + "\n")


def run_sim(args):
    report_port, cmd_port = args.report_port, args.cmd_port
    log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    fleet = subprocess.Popen([
        sys.executable, os.path.join(REPO, "tools/simfleet.py"),
        "--devices", str(args.devices), "--protocol", "v1", "--target", "127.0.0.1",
        "--report-port", str(report_port), "--cmd-port", str(cmd_port),
        "--hb-interval", "1.0", "--boot-secs", "1.0", "--meter-interval", "0",
        "--sync-skew-ms", str(args.sync_skew_ms), "--sync-jitter-ms", str(args.sync_jitter_ms),
    ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
    leader = Leader(report_port, cmd_port, "127.0.0.1")
    try:
        time.sleep(3.0)                 # boot
        leader.pump(args.settle)        # sync
        schedule = leader.fire_burst(args.cues, int(args.lead_ms * 1e6),
                                     int(args.gap_ms * 1e6))
        time.sleep(args.lead_ms / 1000.0 + args.cues * args.gap_ms / 1000.0 + 1.5)
    finally:
        fleet.terminate()
        try:
            fleet.wait(timeout=5)
        except subprocess.TimeoutExpired:
            fleet.kill()
        leader.close()
    log.flush()
    with open(log.name) as source:
        text = source.read()
    os.unlink(log.name)
    fires = parse_fires(text)
    spreads = spread_stats(fires)
    report = args.report or os.path.join(REPO, "tools", "sync-baseline-report.md")
    write_report(report, args, leader.offsets, leader.mac_to_id, schedule, fires, spreads)
    heard = len(spreads)
    if spreads:
        worst = max(spreads.values()) / 1e6
        print(f"measured {heard}/{args.cues} cues; max spread {worst:.3f} ms; "
              f"report -> {report}")
    else:
        print(f"no cue heard on >=2 devices; report -> {report}")
    return 0 if heard >= 1 else 1


def run_hardware(args):
    # No sim launch, no stdout parsing: real Pis record fire evidence externally.
    print("hardware mode: assuming real bopos.py nodes on the LAN "
          f"(cmd {args.cmd_port} / reports {args.report_port}).")
    leader = Leader(args.report_port, args.cmd_port, args.target)
    try:
        print(f"syncing for {args.settle}s ...")
        leader.pump(args.settle)
        for uid, off in sorted(leader.offsets.items()):
            print(f"  {uid} (id {leader.mac_to_id.get(uid, '?')}): offset {off/1e6:.3f} ms")
        if not leader.offsets:
            print("  no pongs -- are nodes running bopos.py and synced?")
        schedule = leader.fire_burst(args.cues, int(args.lead_ms * 1e6),
                                     int(args.gap_ms * 1e6))
        print("fired burst; expected fire instants (leader monotonic ns) -- align "
              "your external recording to these:")
        for cue_id in sorted(schedule, key=lambda c: int(c[1:]) if c[1:].isdigit() else c):
            print(f"  {cue_id}: {schedule[cue_id]}")
        time.sleep(args.lead_ms / 1000.0 + args.cues * args.gap_ms / 1000.0 + 0.5)
    finally:
        leader.close()
    print("Collect the external recording and compute cross-device spread by hand "
          "(or feed bopos.py stdout through parse_fires). This is the sync-4 run.")
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=("sim", "hardware"), default="sim")
    parser.add_argument("--devices", type=int, default=5)
    parser.add_argument("--sync-skew-ms", type=float, default=40.0)
    parser.add_argument("--sync-jitter-ms", type=float, default=2.0)
    parser.add_argument("--cues", type=int, default=8)
    parser.add_argument("--settle", type=float, default=4.0, help="seconds to sync before firing")
    parser.add_argument("--lead-ms", type=float, default=500.0, help="first cue this far ahead")
    parser.add_argument("--gap-ms", type=float, default=250.0, help="spacing between cues")
    parser.add_argument("--report", help="report path (sim mode; default tools/sync-baseline-report.md)")
    parser.add_argument("--report-port", type=int, default=5550)
    parser.add_argument("--cmd-port", type=int, default=6660)
    parser.add_argument("--target", default="255.255.255.255", help="fleet address (hardware mode)")
    return parser.parse_args()


def main():
    args = parse_args()
    return run_hardware(args) if args.mode == "hardware" else run_sim(args)


if __name__ == "__main__":
    raise SystemExit(main())
