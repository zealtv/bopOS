#!/usr/bin/env python3
"""Soak-test an I2C peripheral over a long cable run and score the result.

Built for the Kite Choir spool pole: the LIS3DH tilt sensor sits in the spool,
the Pi sits ~1 m above it, and the I2C hop travels Cat-5/6 + RJ45 alongside the
speaker cable. Bus faults there are intermittent, so a one-shot `i2cdetect`
proves nothing -- this hammers the bus for hours, classifies every failure, and
reports whether the failures cluster.

Two failure modes matter and they are not the same thing:

  * a transaction that FAILS -- NACK / timeout / EIO. The kernel tells us.
  * a transaction that SUCCEEDS and returns the WRONG BYTES. Nothing tells us,
    so every cycle re-reads WHO_AM_I, whose value is a known constant. A byte
    that comes back as anything but 0x33 is bus corruption caught red-handed.

A third mode is worse than both: a wedged bus, where the ioctl blocks forever
instead of returning (a flaky Qwiic cable does this -- `i2cdetect` stalls
mid-scan). An unguarded soak script hangs there silently and the run is lost, so
every transaction runs under a SIGALRM watchdog and a stall is recorded as its
own event class.

And a fourth, which is the one this test exists to catch (measured on Finn Jet,
2026-08-14). The Cat-5 run carries 3V3 as well as the signals, so a marginal
cable does not merely corrupt a transaction -- it can BROWN OUT THE SENSOR. The
LIS3DH then comes back at its power-down reset default (CTRL_REG1 = 0x07), where
it answers the bus perfectly, returns a correct WHO_AM_I, and emits frozen zeros
forever. Every counter above stays clean. So the soak re-reads CTRL_REG1
periodically and after every error burst, and treats a config reset as a
first-class failure: the chip having gone back to its reset state is positive
proof the cable dropped power, which no error counter can show.

The corollary, and it inverts the naive reading of any soak log: A BURST OF
ERRORS THAT STOPS IS NOT A CABLE THAT RECOVERED. It is equally consistent with a
sensor that came back dead. Only the config read-back tells the two apart.

Usage:
  # quick 15-minute confidence check
  i2c_soak.py run --label bench-quiet --out soak.jsonl

  # the real thing: a working day, speakers driven at max volume
  i2c_soak.py run --duration 28800 --label pole-1m-speakers-max --out soak.jsonl

  i2c_soak.py summarize soak.jsonl

Run the same duration twice -- once with the speakers silent, once at max
volume, cables routed as they will actually sit -- and compare. A quiet bench
test proves nothing about the real interferer.

Requires smbus2 and a real I2C bus; refuses to run without one rather than
pretending. Python 3 + smbus2 only, no other third-party deps.
"""

import argparse
import json
import os
import signal
import socket
import sys
import time

try:
    from smbus2 import SMBus, i2c_msg
    HAVE_SMBUS = True
except ImportError:
    HAVE_SMBUS = False

# LIS3DH registers. WHO_AM_I is the canary: a fixed value we can check every
# cycle, which is what turns "the read succeeded" into "the read was correct".
REG_WHO_AM_I = 0x0F
WHO_AM_I_VALUE = 0x33
REG_CTRL1 = 0x20
REG_CTRL4 = 0x23
REG_OUT_X_L = 0x28
AUTO_INCREMENT = 0x80

REG_STATUS = 0x27

CTRL1_100HZ_XYZ = 0x57      # ODR 100 Hz, normal mode, all three axes enabled
CTRL4_HIGH_RES = 0x08       # high-resolution, +/-2 g
CTRL1_POWER_DOWN = 0x07     # the reset default -- what a browned-out chip reads back as
STATUS_ZYXDA = 0x08         # a new x/y/z sample is ready

# Successful reads in one bucket with a byte-identical payload throughout before
# we call the sensor frozen. In high-resolution mode the low bits dither with
# thermal noise even on a dead-still bench, so an unchanging payload means the
# chip is not converting -- not that the spool sat still.
FROZEN_BUCKET_READS = 100

# Consecutive failures before we call the bus wedged rather than glitchy.
WEDGE_THRESHOLD = 50

# errno -> the name that means something to a person reading the summary. Keyed
# by Linux numeric values on purpose: EREMOTEIO does not exist in macOS's errno
# module, and this file gets edited on the Mac and run on the Pi.
ERRNO_NAMES = {
    121: "nack",        # EREMOTEIO -- nobody acknowledged; the classic I2C failure
    110: "timeout",     # ETIMEDOUT -- clock stretched past the driver's patience
    5: "io",            # EIO       -- generic transfer failure
    16: "busy",         # EBUSY     -- a kernel driver owns the address
    6: "noaddr",        # ENXIO     -- no such device or address
    11: "again",        # EAGAIN    -- lost arbitration
}


class Stalled(Exception):
    """A transaction blocked past the watchdog -- the bus is wedged, not merely erroring."""


def _alarm(signum, frame):
    raise Stalled()


class Watchdog:
    """Bound a blocking ioctl with SIGALRM.

    A wedged I2C bus blocks in the kernel rather than returning an error. This
    turns that hang into an exception so the soak keeps running and keeps
    logging. Caveat: if the ioctl is in truly uninterruptible sleep the signal
    cannot land and the process still hangs -- rare, and at that point the bus
    needs a power cycle anyway. Main thread only.
    """

    def __init__(self, seconds):
        self.seconds = seconds

    def __enter__(self):
        signal.signal(signal.SIGALRM, _alarm)
        signal.setitimer(signal.ITIMER_REAL, self.seconds)

    def __exit__(self, exc_type, exc, tb):
        signal.setitimer(signal.ITIMER_REAL, 0)
        return False


def bus_clock_hz(bus):
    """Best-effort read of the configured bus speed, so the log records the condition.

    Bus speed is set in /boot/firmware/config.txt, not at runtime, and it is the
    first thing to change if the run is marginal -- so a soak result is
    meaningless without it. Returns None when it cannot be determined.
    """
    path = "/sys/bus/i2c/devices/i2c-{}/of_node/clock-frequency".format(bus)
    try:
        with open(path, "rb") as f:
            raw = f.read(4)
        if len(raw) == 4:
            return int.from_bytes(raw, "big")
    except OSError:
        pass
    return None


def classify(exc):
    """Map an exception from a transaction onto a stable failure-class name."""
    if isinstance(exc, Stalled):
        return "stall", None
    err = getattr(exc, "errno", None)
    if err is None:
        return "other", None
    return ERRNO_NAMES.get(err, "errno{}".format(err)), err


def configure(bus, addr, timeout):
    """Wake the accelerometer into continuous 100 Hz conversion."""
    with Watchdog(timeout):
        bus.write_byte_data(addr, REG_CTRL1, CTRL1_100HZ_XYZ)
        bus.write_byte_data(addr, REG_CTRL4, CTRL4_HIGH_RES)


def verify_config(bus, addr, timeout):
    """Read back the config we wrote, to catch a chip that power-cycled mid-soak.

    This is the counterpart to the WHO_AM_I canary. WHO_AM_I proves the bus moved
    the right bits; CTRL_REG1 proves the DEVICE is still the one we set up. They
    fail independently: a browned-out LIS3DH returns a perfect WHO_AM_I from its
    reset state while reporting nothing.

    Returns (ctrl1, ctrl4, status). Raises on any transport failure.
    """
    with Watchdog(timeout):
        ctrl1 = bus.read_byte_data(addr, REG_CTRL1)
        ctrl4 = bus.read_byte_data(addr, REG_CTRL4)
        status = bus.read_byte_data(addr, REG_STATUS)
    return ctrl1, ctrl4, status


def config_is_lost(ctrl1, ctrl4):
    """Has the device fallen back to its reset defaults?

    Compares against what configure() wrote. CTRL_REG1 == 0x07 is the specific
    signature of a power-down reset and worth naming, but any mismatch means the
    device is no longer configured the way the soak assumes.
    """
    return ctrl1 != CTRL1_100HZ_XYZ or ctrl4 != CTRL4_HIGH_RES


def bucket_is_frozen(ok_reads, moved):
    """Did this bucket produce plenty of good reads and no change at all?

    Kept separate from the loop so the rule can be argued with and tested. The
    read count matters: a handful of identical payloads is a still sensor, a
    hundred is a dead one.
    """
    return ok_reads >= FROZEN_BUCKET_READS and not moved


def probe(bus, addr, timeout):
    """One soak cycle: the canary read, then a real multi-byte burst.

    Both halves earn their place. The single-byte WHO_AM_I read is the integrity
    check. The 6-byte burst is the realistic load -- a combined write/read with a
    repeated start, which is what an actual driver does and what long runs
    actually struggle with, because it holds the bus for six more clocked bytes
    with no chance to resynchronise.

    Returns (who_am_i, xyz_bytes). Raises on any transport failure.
    """
    with Watchdog(timeout):
        who = bus.read_byte_data(addr, REG_WHO_AM_I)

    write = i2c_msg.write(addr, [REG_OUT_X_L | AUTO_INCREMENT])
    read = i2c_msg.read(addr, 6)
    with Watchdog(timeout):
        bus.i2c_rdwr(write, read)
    return who, bytes(read)


class Report:
    """JSONL to the report file, human-readable lines to stdout.

    Every event is flushed as it happens. A soak that dies at hour six should
    still have five hours of evidence on disk, and clusters are only visible if
    the timestamps survive.
    """

    def __init__(self, path):
        self.fh = open(path, "a", buffering=1) if path else None

    def emit(self, event, human=None):
        if self.fh:
            self.fh.write(json.dumps(event, sort_keys=True) + "\n")
        if human:
            print(human, flush=True)

    def close(self):
        if self.fh:
            self.fh.close()


def run(args):
    if not HAVE_SMBUS:
        sys.exit("smbus2 not installed -- pip install smbus2 (python3-smbus2 on Pi OS)")
    if not os.path.exists("/dev/i2c-{}".format(args.bus)):
        sys.exit("no /dev/i2c-{} -- enable I2C (raspi-config) or pick another --bus"
                 .format(args.bus))

    report = Report(args.out)
    started = time.time()
    clock = bus_clock_hz(args.bus)

    meta = {
        "event": "start",
        "label": args.label,
        "host": socket.gethostname(),
        "started": started,
        "started_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(started)),
        "address": "0x{:02x}".format(args.address),
        "bus": args.bus,
        "clock_hz": clock,
        "duration_s": args.duration,
        "interval_s": args.interval,
        "bucket_s": args.bucket,
        "timeout_s": args.timeout,
    }
    report.emit(meta,
                "soak start  label={}  addr=0x{:02x}  bus={}  clock={}  duration={}s".format(
                    args.label, args.address, args.bus,
                    "{} Hz".format(clock) if clock else "unknown", args.duration))
    if clock is None:
        print("  note: bus clock unknown -- record it by hand, the verdict depends on it",
              flush=True)

    bus = SMBus(args.bus)

    # A configure failure is not a soak result, it is a broken setup. Say so
    # plainly rather than logging eight hours of identical errors.
    try:
        configure(bus, args.address, args.timeout)
    except (OSError, Stalled) as exc:
        kind, _ = classify(exc)
        report.emit({"event": "setup_failed", "kind": kind, "detail": str(exc)})
        report.close()
        sys.exit("cannot configure device at 0x{:02x} ({}) -- check wiring before soaking"
                 .format(args.address, kind))

    totals = {}
    txns = 0
    failures = 0
    corruptions = 0
    stalls = 0
    consecutive = 0
    longest_clean = 0
    clean_run = 0
    wedges = 0
    in_wedge = False
    worst_bucket = {"index": None, "errors": 0}

    bucket_index = 0
    bucket_start = started
    bucket_txns = 0
    bucket_errors = 0
    bucket_ok = 0
    bucket_moved = False

    # Stuck-data detection. Transactions can all succeed while the sensor sits
    # frozen, so liveness is judged PER BUCKET rather than over the run: a
    # run-lifetime "did it ever move" flag latches true in the first minute and
    # then cannot report the sensor dying at hour six, which is precisely the
    # failure a cable soak is looking for.
    prev_payload = None
    payload_changed = False
    frozen_buckets = 0

    # Config-reset detection -- see verify_config().
    resets = 0
    last_config_check = 0

    interrupted = False

    def finish_bucket(now):
        nonlocal bucket_index, bucket_start, bucket_txns, bucket_errors, worst_bucket
        nonlocal bucket_ok, bucket_moved, frozen_buckets
        frozen = bucket_is_frozen(bucket_ok, bucket_moved)
        entry = {
            "event": "bucket",
            "index": bucket_index,
            "t": round(bucket_start - started, 3),
            "txns": bucket_txns,
            "ok": bucket_ok,
            "errors": bucket_errors,
            "moved": bucket_moved,
            "frozen": frozen,
        }
        report.emit(entry)
        if frozen:
            frozen_buckets += 1
            report.emit(
                {"event": "frozen", "t": round(bucket_start - started, 3),
                 "index": bucket_index, "reads": bucket_ok},
                "{:9.2f}s  *** SENSOR FROZEN *** {} good reads in bucket #{}, payload never "
                "changed -- the bus is fine and the data is worthless".format(
                    bucket_start - started, bucket_ok, bucket_index))
        if bucket_errors > worst_bucket["errors"]:
            worst_bucket = {"index": bucket_index, "errors": bucket_errors}
        bucket_index += 1
        bucket_start = now
        bucket_txns = 0
        bucket_errors = 0
        bucket_ok = 0
        bucket_moved = False

    def check_config(elapsed, why):
        """Read the config back; on a reset, say so loudly and re-arm the device.

        Re-arming is deliberate. Leaving the chip powered down would turn one
        brownout into an eight-hour run of frozen data and tell us nothing more,
        whereas re-configuring lets the soak keep counting -- and the reset count
        is itself the headline result.
        """
        nonlocal resets
        try:
            ctrl1, ctrl4, status = verify_config(bus, args.address, args.timeout)
        except (OSError, Stalled) as exc:
            kind, err = classify(exc)
            report.emit(
                {"event": "config_check_failed", "t": round(elapsed, 3),
                 "kind": kind, "errno": err, "why": why},
                "{:9.2f}s  config read-back failed ({})".format(elapsed, kind))
            return
        if not config_is_lost(ctrl1, ctrl4):
            return
        resets += 1
        powered_down = ctrl1 == CTRL1_POWER_DOWN
        report.emit(
            {"event": "config_reset", "t": round(elapsed, 3), "why": why,
             "ctrl1": ctrl1, "ctrl4": ctrl4, "status": status,
             "power_down_default": powered_down, "count": resets},
            "{:9.2f}s  *** DEVICE RESET *** CTRL1=0x{:02x} CTRL4=0x{:02x} STATUS=0x{:02x}{} -- "
            "the sensor lost power, so the CABLE dropped 3V3. It would answer the bus "
            "perfectly and report frozen zeros from here on.".format(
                elapsed, ctrl1, ctrl4, status,
                " (power-down reset default)" if powered_down else ""))
        try:
            configure(bus, args.address, args.timeout)
            report.emit({"event": "reconfigured", "t": round(elapsed, 3)},
                        "{:9.2f}s  device re-armed; soak continues".format(elapsed))
        except (OSError, Stalled) as exc:
            kind, _ = classify(exc)
            report.emit({"event": "reconfigure_failed", "t": round(elapsed, 3), "kind": kind},
                        "{:9.2f}s  re-arm FAILED ({})".format(elapsed, kind))

    try:
        while True:
            now = time.time()
            elapsed = now - started
            if elapsed >= args.duration:
                break
            if now - bucket_start >= args.bucket:
                finish_bucket(now)

            txns += 1
            bucket_txns += 1
            try:
                who, payload = probe(bus, args.address, args.timeout)
            except (OSError, Stalled) as exc:
                kind, err = classify(exc)
                failures += 1
                bucket_errors += 1
                consecutive += 1
                clean_run = 0
                totals[kind] = totals.get(kind, 0) + 1
                if kind == "stall":
                    stalls += 1
                report.emit(
                    {"event": "error", "t": round(elapsed, 3), "kind": kind,
                     "errno": err, "consecutive": consecutive},
                    "{:9.2f}s  ERROR  {:<8} (consecutive {})".format(elapsed, kind, consecutive))

                if consecutive >= WEDGE_THRESHOLD and not in_wedge:
                    in_wedge = True
                    wedges += 1
                    report.emit(
                        {"event": "wedge", "t": round(elapsed, 3), "consecutive": consecutive},
                        "{:9.2f}s  *** BUS WEDGED *** {} consecutive failures -- "
                        "this is not a glitch".format(elapsed, consecutive))
                    if args.stop_on_wedge:
                        break
                time.sleep(args.interval)
                continue

            # Transport succeeded. Now: were the bytes right, and is it still
            # the device we configured?
            burst_ended = consecutive
            consecutive = 0
            bucket_ok += 1
            if in_wedge:
                in_wedge = False
                report.emit({"event": "unwedged", "t": round(elapsed, 3)},
                            "{:9.2f}s  bus answering again after a wedge -- NOT yet proof of "
                            "recovery, checking the device config".format(elapsed))

            if who != WHO_AM_I_VALUE:
                corruptions += 1
                bucket_errors += 1
                clean_run = 0
                totals["corrupt"] = totals.get("corrupt", 0) + 1
                report.emit(
                    {"event": "corruption", "t": round(elapsed, 3),
                     "expected": WHO_AM_I_VALUE, "got": who},
                    "{:9.2f}s  CORRUPT  who_am_i=0x{:02x} expected 0x{:02x} -- "
                    "silent data error".format(elapsed, who, WHO_AM_I_VALUE))
            else:
                clean_run += 1
                longest_clean = max(longest_clean, clean_run)

            if prev_payload is not None and payload != prev_payload:
                payload_changed = True
                bucket_moved = True
            prev_payload = payload

            # The end of an error burst is the single most important moment to
            # check: "the errors stopped" is exactly the observation that looks
            # like recovery and is indistinguishable from a sensor that came back
            # in its reset state.
            if burst_ended or (txns - last_config_check) >= args.config_check:
                last_config_check = txns
                check_config(elapsed, "burst-end" if burst_ended else "periodic")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        interrupted = True
        print("\ninterrupted -- summarising what we have", flush=True)
    finally:
        bus.close()

    finish_bucket(time.time())
    elapsed = time.time() - started
    errors_total = failures + corruptions
    rate = (errors_total / txns) if txns else 0.0
    verdict, reasoning = judge(txns, errors_total, corruptions, stalls, wedges,
                              rate, payload_changed, worst_bucket, resets, frozen_buckets)

    summary = {
        "event": "summary",
        "label": args.label,
        "elapsed_s": round(elapsed, 1),
        "interrupted": interrupted,
        "transactions": txns,
        "failures": failures,
        "corruptions": corruptions,
        "stalls": stalls,
        "wedges": wedges,
        "errors_total": errors_total,
        "error_rate": rate,
        "by_kind": totals,
        "longest_clean_run": longest_clean,
        "worst_bucket": worst_bucket,
        "payload_changed": payload_changed,
        "resets": resets,
        "frozen_buckets": frozen_buckets,
        "clock_hz": clock,
        "verdict": verdict,
        "reasoning": reasoning,
    }
    report.emit(summary, format_summary(summary))
    report.close()
    return 0 if verdict == "PASS" else 1


def judge(txns, errors, corruptions, stalls, wedges, rate, payload_changed, worst_bucket,
          resets=0, frozen_buckets=0):
    """Turn the counters into a verdict.

    The thresholds are judgement calls, written down here so they can be argued
    with rather than buried. The bias is deliberately harsh: this result gates a
    54-unit PCB order, and a bus that is marginal on the bench will be worse in a
    field of 54 poles in the sun with the speakers driven hard.

    Note on remedies (2026-08-14): the adapter board no longer carries an onboard
    LTC4311 footprint, so the cheap on-board levers are the passive ones --
    pull-up value, bus clock, routing. Active termination is still available, but
    as a separate Adafruit LTC4311 Qwiic breakout, which means an extra module,
    an extra connector and extra cost on every one of 54 units. So it is a real
    fallback and not a free one: exhaust the passive levers first.
    """
    if txns == 0:
        return "INVALID", "no transactions completed"
    if resets:
        return "FAIL", ("the device reset {} time(s) mid-soak -- it came back at its "
                        "power-down defaults, which means the cable dropped 3V3 to the "
                        "sensor. In the field that is a spool reporting frozen zeros with "
                        "nothing in any log to show it".format(resets))
    if frozen_buckets:
        return "FAIL", ("{} bucket(s) of good reads with a byte-identical payload throughout "
                        "-- the bus worked and the data was dead. Confirm the sensor was free "
                        "to move; if it was, this is the silent failure the soak exists to "
                        "catch".format(frozen_buckets))
    if wedges or stalls:
        return "FAIL", ("bus wedged/stalled -- a hung bus needs a power cycle on site, "
                        "which is unacceptable across 54 units")
    if corruptions:
        return "FAIL", ("silent data corruption observed -- WHO_AM_I came back wrong, so "
                        "sensor readings cannot be trusted either")
    if not payload_changed:
        return "SUSPECT", ("every transaction succeeded but the payload never changed -- "
                           "move the sensor during the soak; if it still never changes, "
                           "the device is not really converting")
    if errors == 0:
        return "PASS", "no transport errors and no corruption over {} transactions".format(txns)
    if rate <= 1e-5 and worst_bucket["errors"] <= 2:
        return "MARGINAL", ("isolated errors at {:.2e} -- works, but has no margin. Re-soak "
                            "with the passive levers first (pull-up value, lower bus clock, "
                            "routing); an LTC4311 Qwiic breakout is the fallback, but it is "
                            "an extra module on all 54 units".format(rate))
    return "FAIL", ("error rate {:.2e} with up to {} errors in one bucket -- "
                    "clustered failures mean a real signal-integrity problem, not noise"
                    .format(rate, worst_bucket["errors"]))


def format_summary(s):
    lines = [
        "",
        "--- soak summary: {} ---".format(s["label"]),
        "  elapsed          {:.0f}s{}".format(s["elapsed_s"],
                                              "  (INTERRUPTED)" if s["interrupted"] else ""),
        "  bus clock        {}".format("{} Hz".format(s["clock_hz"]) if s["clock_hz"] else "unknown"),
        "  transactions     {}".format(s["transactions"]),
        "  transport errors {}".format(s["failures"]),
        "  corruptions      {}".format(s["corruptions"]),
        "  stalls / wedges  {} / {}".format(s["stalls"], s["wedges"]),
        "  error rate       {:.3e}".format(s["error_rate"]),
        "  longest clean    {} transactions".format(s["longest_clean_run"]),
        "  payload moved    {}".format("yes" if s["payload_changed"] else "NO -- see verdict"),
        "  device resets    {}".format(s.get("resets", 0)),
        "  frozen buckets   {}".format(s.get("frozen_buckets", 0)),
    ]
    if s["by_kind"]:
        lines.append("  by kind          " + ", ".join(
            "{}={}".format(k, v) for k, v in sorted(s["by_kind"].items())))
    if s["worst_bucket"]["index"] is not None:
        lines.append("  worst bucket     #{} with {} errors".format(
            s["worst_bucket"]["index"], s["worst_bucket"]["errors"]))
    lines += ["", "  VERDICT: {}".format(s["verdict"]), "  {}".format(s["reasoning"]), ""]
    return "\n".join(lines)


def summarize(args):
    """Re-print the summaries in a report file, so runs can be compared side by side."""
    found = 0
    for line in open(args.path):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("event") == "summary":
            found += 1
            print(format_summary(entry))
    if not found:
        print("no completed runs in {} -- a soak still in progress writes its summary "
              "only at the end".format(args.path))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="soak the bus and score it")
    r.add_argument("--duration", type=float, default=900,
                   help="seconds to soak (default 900; use 28800 for a working day)")
    r.add_argument("--label", default="unlabelled",
                   help="what this run tests, e.g. pole-1m-speakers-max")
    r.add_argument("--address", type=lambda x: int(x, 0), default=0x19,
                   help="I2C address (default 0x19, the spool LIS3DH)")
    r.add_argument("--bus", type=int, default=1, help="I2C bus number (default 1)")
    r.add_argument("--interval", type=float, default=0.02,
                   help="seconds between cycles (default 0.02 = 50 Hz)")
    r.add_argument("--bucket", type=float, default=60,
                   help="seconds per reporting bucket, for clustering (default 60)")
    r.add_argument("--timeout", type=float, default=2.0,
                   help="watchdog seconds before a transaction counts as a stall (default 2)")
    r.add_argument("--config-check", type=int, default=250, dest="config_check",
                   help="read CTRL_REG1/4 back every N transactions to catch a device that "
                        "power-cycled (default 250; also always checked after an error burst)")
    r.add_argument("--out", default=None, help="append JSONL report events to this file")
    r.add_argument("--stop-on-wedge", action="store_true",
                   help="stop at the first wedge instead of logging through it")
    r.set_defaults(func=run)

    s = sub.add_parser("summarize", help="print the summaries in a report file")
    s.add_argument("path")
    s.set_defaults(func=summarize)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
