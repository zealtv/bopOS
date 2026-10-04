#!/usr/bin/env python3
"""
Timestamping, size-capped log sink for the bopOS run scripts.

Reads lines on stdin, writes them to a logfile with a timestamp prefix, and
stops growing the file once a byte cap is reached. Used by `bash/start.sh` so
the diagnostics `python/io/main.py` and `python/bopos.py` already print reach
someone; see loom stitch `59-i2c-inventory/0-bridge-logging`.

    <cmd> 2>&1 | logpipe.py <path> [max-bytes]

Why a cap rather than tail rotation: the log this exists for is an unattended
I2C cable soak, where a marginal bus writes an error line every poll cycle for
hours. What the operator needs from that file is the *onset* and the
distribution of errors over time, so keeping the newest bytes and discarding
the beginning throws away the diagnostic half. We keep the head, note the cap
in the file, and report how much was discarded when the run ends.

One generation of history is kept: an existing logfile is moved to
`<path>.prev` at startup, so the previous boot survives exactly one reboot.
In Performance the sink resolves every entry to tmpfs (bounded at 4 MiB) or
process memory, reading the daemon's remembered mode. A Performance boot
does not open or rotate the SD log. RAM is never copied back on exit.

Not `nodelog.py`. That is the Bob-ratified append-only *node log* facility
(thread `42-node-logging`): a structured `stream<TAB>values` API for callers
inside a process, written under a configurable destination, with daily files
and a per-file cap that continues into `-N` siblings. This is a dumb sink for
a process's stdout/stderr, living beside the pid files in `run/`, bounded in
total. Routing service output into the node log is a question for thread 42,
not a redirection.

Timestamps match nodelog's shape -- ISO-8601 local civil time with offset and
millisecond precision -- so lines from the two files read the same way.
"""

import os
import signal
import sys
from datetime import datetime
from collections import deque

import performance_mode

# ~128 MiB. Measured on Finn Jet 2026-08-14 with a LIS3DH physically pulled off
# the bus: a continuously failing peripheral writes 1670 B/s -- 5.7 MiB/hour,
# 20 lines/s, because a failed poll logs twice (the peripheral's own error and
# the manager's). So this holds ~22 hours of unbroken errors, where an 8-hour
# working-day soak needs ~46 MiB. A healthy bus at the same poll rate writes
# nothing at all (measured: zero bytes in 30s), so the cap only ever engages in
# the fault case. Either way it stays a rounding error on an SD card.
DEFAULT_MAX_BYTES = 128 * 1024 * 1024


class PerformanceSink:
    """Re-resolve before every write, including startup and shutdown markers.

    Both service sinks observe the daemon's durable mode file. No service
    restart is needed; a boot already in Performance never opens an SD log.
    On hosts without tmpfs a bounded deque is the RAM destination.
    """

    def __init__(self, path, root=None):
        self.path = path
        self.root = root or os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.mode_path = os.path.join(self.root, "state", "performance.json")
        self.handle = None
        self.current = None
        self.started = set()
        self.memory = deque(maxlen=4096)
        self.ram_bytes = 0
        self.ram_failed = False

    def write(self, line):
        try:
            self._write(line)
        except OSError:
            if not performance_mode.load(self.mode_path):
                raise
            # A full/unavailable tmpfs must not kill a sink and break its
            # service's stdout pipe. Keep diagnostics in bounded memory.
            self.ram_failed = True
            try:
                self.close()
            except OSError:
                self.handle = None
            self.memory.append(line[:4096])

    def _write(self, line):
        active = performance_mode.load(self.mode_path)
        if not active:
            self.ram_failed = False
        ram = performance_mode.ram_directory(self.root) if active and not self.ram_failed else None
        destination = (os.path.join(ram, os.path.basename(self.path))
                       if ram else None) if active else self.path
        if destination != self.current or (destination and self.handle is None):
            self.close()
            self.current = destination
            if destination:
                os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
                if destination not in self.started and os.path.exists(destination):
                    os.replace(destination, destination + ".prev")
                self.started.add(destination)
                self.handle = open(destination, "a", buffering=1, errors="replace")
        if active:
            # Service diagnostics cannot consume all of a small Pi's tmpfs.
            if self.ram_bytes + len(line.encode("utf-8")) > 4 * 1024 * 1024:
                return
            self.ram_bytes += len(line.encode("utf-8"))
        if self.handle is None:
            self.memory.append(line[:4096])
        else:
            self.handle.write(line)

    def close(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def stamp():
    now = datetime.now().astimezone()
    offset = now.strftime("%z")
    return "%s.%03d%s:%s" % (now.strftime("%Y-%m-%dT%H:%M:%S"),
                             now.microsecond // 1000, offset[:3], offset[3:])


def main(argv):
    if len(argv) < 2:
        sys.stderr.write("usage: logpipe.py <path> [max-bytes]\n")
        return 2

    path = argv[1]
    try:
        max_bytes = int(argv[2]) if len(argv) > 2 else DEFAULT_MAX_BYTES
    except ValueError:
        sys.stderr.write("logpipe.py: max-bytes must be an integer\n")
        return 2

    # Terminate cleanly on stop.sh's SIGTERM so the epilogue still gets written.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    written = 0
    discarded = 0
    last_discarded_at = None

    with PerformanceSink(path) as log:
        header = "%s --- logpipe: capping %s at %d bytes ---\n" % (
            stamp(), os.path.basename(path), max_bytes)
        log.write(header)
        written += len(header)

        try:
            for raw in sys.stdin:
                line = "%s %s" % (stamp(), raw if raw.endswith("\n") else raw + "\n")
                if written + len(line) > max_bytes:
                    if not discarded:
                        note = ("%s --- logpipe: size cap reached; the head of this "
                                "run is kept and further output is discarded ---\n" % stamp())
                        log.write(note)
                        written += len(note)
                    discarded += 1
                    last_discarded_at = stamp()
                    continue
                log.write(line)
                written += len(line)
        except (KeyboardInterrupt, SystemExit):
            pass
        except OSError as error:
            log.write("%s --- logpipe: read failed: %s ---\n" % (stamp(), error))
        finally:
            if discarded:
                log.write("%s --- logpipe: %d line(s) discarded after the cap, "
                          "last at %s ---\n" % (stamp(), discarded, last_discarded_at))
            log.write("%s --- logpipe: input closed ---\n" % stamp())

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
