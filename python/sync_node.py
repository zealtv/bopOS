"""Node-side clock sync (contract sec 3.1): hold the leader-pushed offset and
fire events at their local monotonic deadline.

Pure timing logic, deliberately free of import-time side effects (no ports, no
pyOSC3) so it can be unit-tested on its own -- bopos.py imports it and wires the
OSC (pong reply, offset push, /e -> engine). All times are integer nanoseconds
from time.monotonic(); offset === deviceClock - leaderClock, so a leader-clock
sharedTime converts to a local deadline as `sharedTime + offset`.
"""
import threading
import time

# A newly pushed offset is slewed in over ~1 s rather than stepped, so audio
# already scheduled doesn't glitch (HB gen-2 adjustScheduleTime). Slew is
# node-internal; the wire only ever carries the absolute target (contract sec 4).
SLEW_DURATION_NS = 1_000_000_000
# Late-fire policy (implementer's call, recorded in the stitch): an event whose
# deadline has just passed is still fired if it is within this grace window --
# a small network hiccup shouldn't drop a downbeat -- but a fire later than this
# is stale and dropped rather than fired wrong. Both cases are logged.
# The name predates the `/cue` retirement (thread 44 child 4) and is kept
# because contract sec 3.1 cites it; it now governs scheduled `/e/*` fires.
CUE_LATE_GRACE_NS = 50_000_000


def _now_ns():
    return time.monotonic_ns()


class SyncState:
    """The working clock offset, slewed toward each pushed target."""

    def __init__(self, slew_ns=SLEW_DURATION_NS, now=_now_ns):
        self._now = now
        self._slew = slew_ns
        self._lock = threading.Lock()
        self._target = None   # last pushed offset, None until first push
        self._prev = 0        # working offset at the moment the target changed
        self._since = 0       # _now() when the target was last set

    def push(self, target):
        with self._lock:
            self._prev = self._working_locked()
            self._target = int(target)
            self._since = self._now()

    def _working_locked(self):
        if self._target is None:
            return 0
        if self._slew <= 0:
            return self._target
        frac = (self._now() - self._since) / self._slew
        if frac >= 1.0:
            return self._target
        return int(self._prev + (self._target - self._prev) * frac)

    def offset(self):
        with self._lock:
            return self._working_locked()

    def synced(self):
        with self._lock:
            return self._target is not None


class EventScheduler:
    """Fires events at `sharedTime + offset` on the local monotonic clock.

    `fire(identity, elements)` sends the bare event to the engine; `log(text)` records
    fire/drop for observability. The offset is re-read every wakeup so a slewing
    correction is tracked right up to the deadline.
    """

    def __init__(self, sync_state, fire, log=print, now=_now_ns,
                 late_grace_ns=CUE_LATE_GRACE_NS, log_label="event"):
        self._sync = sync_state
        self._fire = fire
        self._log = log
        self._now = now
        self._grace = late_grace_ns
        self._label = str(log_label)
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._pending = []   # [ [shared_ns, identity, elements], ... ]
        self._thread = None
        self._running = False

    def schedule(self, shared_ns, identity, elements):
        with self._lock:
            self._pending.append(
                [int(shared_ns), str(identity), list(elements)])
        self._wake.set()

    def start(self):
        if self._thread is not None:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="event-scheduler",
                                        daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _loop(self):
        while self._running:
            now = self._now()
            offset = self._sync.offset()
            due = []
            with self._lock:
                remaining = []
                for shared, identity, elements in self._pending:
                    if now >= shared + offset:
                        due.append((identity, elements, now - (shared + offset)))
                    else:
                        remaining.append([shared, identity, elements])
                self._pending = remaining
                nearest = min(
                    (shared + offset for shared, _identity, _elements
                     in self._pending),
                    default=None)
            # fire outside the lock: fire()/log() may touch a socket
            for identity, elements, late in due:
                if late <= self._grace:
                    self._fire(identity, elements)
                    # fire_mono is machine-parseable for the sync-3 measure tool
                    # (same token as simfleet); late is human context
                    self._log("{} {} fired fire_mono={} (late {:.1f}ms)".format(
                        self._label, identity, now, late / 1e6))
                else:
                    self._log("{} {} DROPPED (late {:.1f}ms > grace)".format(
                        self._label, identity, late / 1e6))
            # sleep until the next deadline, capped so a slewing offset is
            # re-evaluated; wake early when a new event is scheduled
            if nearest is None:
                self._wake.wait()
            else:
                self._wake.wait(timeout=max(0.0, min((nearest - self._now()) / 1e9, 0.02)))
            self._wake.clear()
