# nodelog.py
"""bopOS node logging facility (OSC contract section 4.2, `/log`).

A shared, append-only, timestamped log. One facility, many streams -- any
bopOS subsystem calls `nodelog.append(stream, values)` directly (the `/log`
engine handler in bopos.py is the first caller; the io bridge and future
features are others). Not one bespoke logger per feature.

Design ratified 2026-07-24 (`.loom/tied/1-logging-seed-design/`):

- The **node** stamps every entry at call time with local civil time,
  ISO-8601 with offset and millisecond precision
  (`2026-07-24T14:03:22.512+01:00`). Absolute time never enters PD (house
  rule); PD only ever sends events or relative intervals.
- Each entry is one plain-text tab-separated line
  `timestamp<TAB>stream<TAB>values...` (values space-joined, as received).
  Plain text so a third party can read a file straight off a USB stick.
- Streams need no declaration; a stream is a short name matching the report
  rule `[A-Za-z0-9_-]+` (bopos.py `report_callback`). Invalid names are
  dropped with a logged warning, never fatal.
- One file per stream per day: `<stream>-YYYY-MM-DD.log`. Daily files *are*
  the rotation. A defensive 50 MB per-file cap guards a runaway caller,
  continuing to `<stream>-YYYY-MM-DD-2.log`, `-3`, ...
- Append + flush per entry, no per-line fsync (SD-card wear). fsync happens
  on stream close and on a destination change. Failure mode on power cut is
  at worst a truncated last line -- acceptable for an append-only log.

Destination resolution is a hook (`destination_dir`). This module ships the
internal default only (`~/bopos-logs/`); the internal/usb choice and its
per-write effective resolution land in stitch `4-log-destination-config`,
which supplies a callable without reshaping anything here.
"""

import os
import re
import threading
from datetime import datetime

# Same rule as report names (bopos.py report_callback). No dots -> no path
# separators, no traversal; a stream name is always one path component.
STREAM_PATTERN = re.compile(r"[A-Za-z0-9_-]+$")

# Defensive per-file cap. Interaction-rate logging never approaches this;
# it only bounds a runaway caller. Beyond it, entries continue in a
# `-N`-suffixed sibling for the same stream and day.
MAX_FILE_BYTES = 50 * 1024 * 1024

# The internal default destination -- the SD card. Stitch 4's `usb` choice
# resolves through the destination hook instead.
DEFAULT_INTERNAL_DIR = os.path.expanduser("~/bopos-logs")


class NodeLog:
    """One append-only log with many streams under a resolved directory.

    `destination_dir` is either a callable returning the effective directory
    (re-evaluated per entry, so a stitch-4 hot USB insert takes effect on the
    next write) or a static path (the internal default). Open file handles are
    kept per path and flushed per line; they are fsync'd and closed when the
    day rolls, the file cap trips, the effective directory changes, or the
    facility is closed.
    """

    def __init__(self, destination_dir=None):
        self._destination = destination_dir or DEFAULT_INTERNAL_DIR
        self._lock = threading.Lock()
        self._handles = {}       # absolute path -> open file object
        self._stream_path = {}   # stream name -> the path it last wrote to

    def destination_dir(self):
        dest = self._destination
        path = dest() if callable(dest) else dest
        return os.path.expanduser(str(path))

    def _target_path(self, directory, stream, date_str):
        """The file this entry appends to: the daily file, or its next
        `-N` continuation once the current one has reached the size cap."""
        base = os.path.join(directory, "{}-{}.log".format(stream, date_str))
        candidate = base
        suffix = 1
        while True:
            try:
                if os.path.getsize(candidate) < MAX_FILE_BYTES:
                    return candidate
            except OSError:
                return candidate  # does not exist yet -> use it
            suffix += 1
            candidate = os.path.join(
                directory, "{}-{}-{}.log".format(stream, date_str, suffix))

    def _handle_for(self, path):
        handle = self._handles.get(path)
        if handle is None:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            handle = open(path, "a", buffering=1)  # line-buffered append
            self._handles[path] = handle
        return handle

    def _retire(self, path):
        handle = self._handles.pop(path, None)
        if handle is None:
            return
        try:
            handle.flush()
            os.fsync(handle.fileno())
        except OSError:
            pass
        finally:
            try:
                handle.close()
            except OSError:
                pass

    def append(self, stream, values):
        """Append one timestamped entry to `stream`. Returns True iff written.

        Never raises: an invalid stream name or a write error is logged and
        dropped so a logging call can never take down its caller."""
        stream = str(stream)
        if STREAM_PATTERN.match(stream) is None:
            print("nodelog: refusing invalid stream {!r}".format(stream))
            return False
        now = datetime.now().astimezone()
        stamp = now.isoformat(timespec="milliseconds")
        date_str = now.strftime("%Y-%m-%d")
        payload = " ".join(str(value) for value in values)
        line = "{}\t{}\t{}\n".format(stamp, stream, payload)
        with self._lock:
            try:
                path = self._target_path(self.destination_dir(), stream, date_str)
                previous = self._stream_path.get(stream)
                if previous is not None and previous != path:
                    # day rolled, cap tripped, or destination changed: fsync
                    # and close the file this stream was writing to.
                    self._retire(previous)
                handle = self._handle_for(path)
                handle.write(line)
                handle.flush()
                self._stream_path[stream] = path
                return True
            except OSError as error:
                print("nodelog: could not append to {!r}: {}".format(stream, error))
                return False

    def close(self):
        """fsync and close every open stream (call at shutdown)."""
        with self._lock:
            for path in list(self._handles):
                self._retire(path)
            self._stream_path.clear()


# Module-level default facility so any subsystem can `nodelog.append(...)`
# without threading an instance through. bopos.py owns configuration:
# stitch 2 leaves the internal default; stitch 4 calls `configure(hook)` with
# the internal/usb resolver.
_instance = None
_instance_lock = threading.Lock()


def configure(destination_dir=None):
    """Install (or replace) the module-level facility, closing any prior one."""
    global _instance
    with _instance_lock:
        if _instance is not None:
            _instance.close()
        _instance = NodeLog(destination_dir)
    return _instance


def instance():
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = NodeLog()
    return _instance


def append(stream, values):
    return instance().append(stream, values)


def close():
    global _instance
    with _instance_lock:
        if _instance is not None:
            _instance.close()
