#!/usr/bin/env python3
"""One timed performance measurement of the running bopOS audio stack.

Samples per-process CPU, SoC temperature, and JACK DSP load over a timed
window, counts xruns appended to a jackd log during that window, and emits
one JSON report line — comparable across runs, machines, and jackd settings.

Usage:
  perf_measure.py run --duration 60 --label p512-n2-r44100 \
      --jack-log /path/to/jackd.log --out reports.jsonl
  perf_measure.py summarize reports.jsonl

Stdlib only. Linux (/proc) preferred; degrades to `ps` elsewhere. Temperature
uses vcgencmd, falling back to sysfs thermal, absent gracefully off-Pi.
"""

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time

# Processes worth watching, as regexes over full command lines.
DEFAULT_PROCS = {
    "jackd": r"jackd",
    "pd": r"(^|/)pd(\s|$)",
    "bopos": r"python.*bopos\.py",
    "io": r"python.*io/main\.py",
}

CLK_TCK = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
HAS_PROC = os.path.isdir("/proc/self")


def find_pids(pattern):
    pids = []
    rx = re.compile(pattern)
    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                with open(f"/proc/{entry}/cmdline", "rb") as f:
                    cmdline = f.read().replace(b"\0", b" ").decode(errors="replace").strip()
            except OSError:
                continue
            if cmdline and rx.search(cmdline) and int(entry) != os.getpid():
                pids.append(int(entry))
    except FileNotFoundError:
        # No /proc (macOS): fall back to ps.
        out = subprocess.run(["ps", "-A", "-o", "pid=,args="],
                             capture_output=True, text=True).stdout
        for line in out.splitlines():
            pid, _, args = line.strip().partition(" ")
            if rx.search(args) and int(pid) != os.getpid():
                pids.append(int(pid))
    return pids


def proc_jiffies(pid):
    """utime+stime for one pid, or None if it is gone."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            fields = f.read().rsplit(")", 1)[1].split()
        return int(fields[11]) + int(fields[12])  # utime, stime
    except (OSError, IndexError, ValueError):
        return None


def ps_pcpu(pid):
    """CPU%% via ps for hosts without /proc (macOS laptop rig)."""
    out = subprocess.run(["ps", "-o", "pcpu=", "-p", str(pid)],
                         capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return None


def proc_nice(pid):
    try:
        return os.getpriority(os.PRIO_PROCESS, pid)
    except OSError:
        return None


def read_temp():
    vcgencmd = shutil.which("vcgencmd")
    if vcgencmd:
        try:
            out = subprocess.run([vcgencmd, "measure_temp"],
                                 capture_output=True, text=True, timeout=5).stdout
            m = re.search(r"([\d.]+)", out)
            if m:
                return float(m.group(1))
        except (subprocess.SubprocessError, OSError):
            pass
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read().strip()) / 1000.0
    except (OSError, ValueError):
        return None


def count_xruns(path, offset):
    """Count xrun mentions appended to a jackd log past byte offset."""
    try:
        with open(path, errors="replace") as f:
            f.seek(offset)
            return sum(1 for line in f if re.search(r"xrun", line, re.I))
    except OSError:
        return None


class DspLoadWatcher:
    """Background jack_cpu_load, if available and JACK is up."""

    def __init__(self):
        self.proc = None
        self.samples = []
        exe = shutil.which("jack_cpu_load")
        if exe:
            try:
                self.proc = subprocess.Popen(
                    [exe], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    text=True)
                os.set_blocking(self.proc.stdout.fileno(), False)
            except OSError:
                self.proc = None

    def poll(self):
        if not self.proc or self.proc.poll() is not None:
            return
        try:
            chunk = self.proc.stdout.read()
        except (OSError, TypeError):
            return
        for line in (chunk or "").splitlines():
            m = re.search(r"([\d.]+)", line)
            if m:
                self.samples.append(float(m.group(1)))

    def stop(self):
        self.poll()
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def run(args):
    procs = {}  # name -> {pid, nice, jiffies0, cpu_samples[]}
    for name, pattern in DEFAULT_PROCS.items():
        pids = find_pids(pattern)
        if pids:
            pid = pids[0]
            procs[name] = {"pid": pid, "nice": proc_nice(pid),
                           "jiffies": proc_jiffies(pid), "samples": []}

    jack_log_offset = 0
    if args.jack_log:
        try:
            jack_log_offset = os.path.getsize(args.jack_log)
        except OSError:
            pass

    dsp = DspLoadWatcher()
    temps = []
    t = read_temp()
    if t is not None:
        temps.append(t)

    start = time.monotonic()
    last = start
    last_jiffies = {n: p["jiffies"] for n, p in procs.items()}
    while time.monotonic() - start < args.duration:
        time.sleep(min(args.interval, max(0.1, args.duration - (time.monotonic() - start))))
        now = time.monotonic()
        dt = now - last
        for name, p in procs.items():
            if HAS_PROC:
                j = proc_jiffies(p["pid"])
                if j is not None and last_jiffies[name] is not None and dt > 0:
                    p["samples"].append(100.0 * (j - last_jiffies[name]) / CLK_TCK / dt)
                last_jiffies[name] = j
            else:
                pcpu = ps_pcpu(p["pid"])
                if pcpu is not None:
                    p["samples"].append(pcpu)
        last = now
        t = read_temp()
        if t is not None:
            temps.append(t)
        dsp.poll()
    dsp.stop()

    def stats(samples):
        if not samples:
            return None
        return {"mean": round(sum(samples) / len(samples), 1),
                "max": round(max(samples), 1)}

    report = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "host": socket.gethostname(),
        "label": args.label,
        "patch": args.patch,
        "duration_s": args.duration,
        "xruns": count_xruns(args.jack_log, jack_log_offset) if args.jack_log else None,
        "dsp_load": stats(dsp.samples),
        "cpu_pct": {n: stats(p["samples"]) for n, p in procs.items()},
        "nice": {n: p["nice"] for n, p in procs.items()},
        "temp_c": {"start": temps[0], "max": max(temps)} if temps else None,
        "load1": os.getloadavg()[0] if hasattr(os, "getloadavg") else None,
        "notes": args.notes,
    }
    line = json.dumps(report)
    if args.out:
        with open(args.out, "a") as f:
            f.write(line + "\n")
    print(line)
    print(format_row(report, header=True), file=sys.stderr)
    print(format_row(report), file=sys.stderr)
    return 0


COLS = ["label", "patch", "xruns", "dsp%", "jackd%", "pd%", "bopos%", "temp°C", "load1"]


def format_row(r, header=False):
    if header:
        return "  ".join(f"{c:>10}" for c in COLS)

    def cpu(name):
        s = (r.get("cpu_pct") or {}).get(name)
        return f"{s['mean']}/{s['max']}" if s else "-"

    dsp = r.get("dsp_load")
    temp = r.get("temp_c")
    vals = [
        r.get("label") or "-",
        r.get("patch") or "-",
        "-" if r.get("xruns") is None else str(r["xruns"]),
        f"{dsp['mean']}/{dsp['max']}" if dsp else "-",
        cpu("jackd"), cpu("pd"), cpu("bopos"),
        f"{temp['start']}→{temp['max']}" if temp else "-",
        "-" if r.get("load1") is None else f"{r['load1']:.2f}",
    ]
    return "  ".join(f"{v:>10}" for v in vals)


def summarize(args):
    print(format_row({}, header=True))
    for path in args.files:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    print(format_row(json.loads(line)))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    runp = sub.add_parser("run", help="measure the running stack")
    runp.add_argument("--duration", type=float, default=60, help="seconds to sample")
    runp.add_argument("--interval", type=float, default=2, help="sample interval seconds")
    runp.add_argument("--label", default=None, help="cell label, e.g. r44100-p512-n2")
    runp.add_argument("--patch", default=None, help="patch name for the report")
    runp.add_argument("--jack-log", default=None, help="jackd log file to count xruns in")
    runp.add_argument("--out", default=None, help="append JSON report line to this file")
    runp.add_argument("--notes", default=None)
    runp.set_defaults(func=run)
    summ = sub.add_parser("summarize", help="print reports as an aligned table")
    summ.add_argument("files", nargs="+")
    summ.set_defaults(func=summarize)
    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
