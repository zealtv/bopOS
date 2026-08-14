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

# ~64 MiB. At the bridge's 10 Hz poll rate a continuously failing peripheral
# writes on the order of 2 MB/hour, so this holds a full working-day soak
# without capping, while staying a rounding error on an SD card.
DEFAULT_MAX_BYTES = 64 * 1024 * 1024


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

    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    try:
        if os.path.exists(path):
            os.replace(path, path + ".prev")
    except OSError as error:
        sys.stderr.write("logpipe.py: could not rotate %s: %s\n" % (path, error))

    # Terminate cleanly on stop.sh's SIGTERM so the epilogue still gets written.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    written = 0
    discarded = 0
    last_discarded_at = None

    with open(path, "a", buffering=1, errors="replace") as log:
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
