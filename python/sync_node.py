"""Node-side clock sync (contract sec 3.1): hold the leader-pushed offset and
fire cues at their local monotonic deadline.

Pure timing logic, deliberately free of import-time side effects (no ports, no
pyOSC3) so it can be unit-tested on its own -- helper.py imports it and wires the
OSC (pong reply, offset push, /cue -> engine). All times are integer nanoseconds
from time.monotonic(); offset === deviceClock - leaderClock, so a leader-clock
sharedTime converts to a local deadline as `sharedTime + offset`.
"""
import threading
import time

# A newly pushed offset is slewed in over ~1 s rather than stepped, so audio
# already scheduled doesn't glitch (HB gen-2 adjustScheduleTime). Slew is
# node-internal; the wire only ever carries the absolute target (contract sec 4).
SLEW_DURATION_NS = 1_000_000_000
# Late-cue policy (implementer's call, recorded in the stitch): a cue whose
# deadline has just passed is still fired if it is within this grace window --
# a small network hiccup shouldn't drop a downbeat -- but a cue later than this
# is stale and dropped rather than fired wrong. Both cases are logged.
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


class CueScheduler:
    """Fires cues at `sharedTime + offset` on the local monotonic clock.

    `fire(cue_id)` sends the bare cue to the engine; `log(text)` records
    fire/drop for observability. The offset is re-read every wakeup so a slewing
    correction is tracked right up to the deadline.
    """

    def __init__(self, sync_state, fire, log=print, now=_now_ns,
                 late_grace_ns=CUE_LATE_GRACE_NS):
        self._sync = sync_state
        self._fire = fire
        self._log = log
        self._now = now
        self._grace = late_grace_ns
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._pending = []   # [ [shared_ns, cue_id], ... ]
        self._thread = None
        self._running = False

    def schedule(self, shared_ns, cue_id):
        with self._lock:
            self._pending.append([int(shared_ns), str(cue_id)])
        self._wake.set()

    def start(self):
        if self._thread is not None:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="cue-scheduler",
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
                for shared, cue_id in self._pending:
                    if now >= shared + offset:
                        due.append((cue_id, now - (shared + offset)))
                    else:
                        remaining.append([shared, cue_id])
                self._pending = remaining
                nearest = min((s + offset for s, _ in self._pending), default=None)
            # fire outside the lock: fire()/log() may touch a socket
            for cue_id, late in due:
                if late <= self._grace:
                    self._fire(cue_id)
                    # fire_mono is machine-parseable for the sync-3 measure tool
                    # (same token as simfleet); late is human context
                    self._log("cue {} fired fire_mono={} (late {:.1f}ms)".format(
                        cue_id, now, late / 1e6))
                else:
                    self._log("cue {} DROPPED (late {:.1f}ms > grace)".format(
                        cue_id, late / 1e6))
            # sleep until the next deadline, capped so a slewing offset is
            # re-evaluated; wake early when a new cue is scheduled
            if nearest is None:
                self._wake.wait()
            else:
                self._wake.wait(timeout=max(0.0, min((nearest - self._now()) / 1e9, 0.02)))
            self._wake.clear()
