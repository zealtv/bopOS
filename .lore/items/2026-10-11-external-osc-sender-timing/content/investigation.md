# Forward-sync timing from external OSC senders — investigation, 2026-10-11

Record of one Claude session with Bob on 2026-10-11. Code references hold
as of bopOS `main` at `b12f582` (session start) and `4390fc3` (reference
page update made in the same session). Statements marked *inferred* come
from reading code, not from running it.

## 1. The question

Bob asked: with bopOS as set up now, does an OSC message meant to use
forward synchronization have to come from the dashboard, or can another
OSC application send one effectively?

## 2. What bopOS does (read from code, 2026-10-11)

- **Nodes accept `/e/*` from any sender.** `bopos.py` checks only the
  selector and the shape: a string time first, then 0–3 floats
  (`python/bopos.py:1607-1631`). No sender-address check.
- **The time lives in the dashboard's clock domain.** `sharedTimeNs` is the
  dashboard backend's `time.monotonic_ns()` plus the lead
  (`dashboard/osc_bridge.py:661-664`). Each node fires at
  `sharedTimeNs + offset`, where the dashboard pushes `offset ≡
  deviceClock − leaderClock` (contract §3.1–3.2). The dashboard's monotonic
  clock counts from roughly when its host booted; an outside app has no way
  to know it.
- **A wrong time fails quietly.** A deadline already passed by more than
  `CUE_LATE_GRACE_NS` (50 ms, `python/sync_node.py:23`) gets logged as
  `DROPPED`. A time far ahead waits in the scheduler with no upper bound
  seen in `EventScheduler`.
- **`"0"` always works**, firing on arrival, unsynchronized.
- **Untested possibility:** a Python script on the dashboard machine itself
  could likely stamp `time.monotonic_ns() + lead`, since macOS's monotonic
  clock is system-wide. Remote apps (TouchOSC, Max on another machine)
  can't.
- **No dashboard ingress restamps outside events.** The dashboard's only
  listening socket takes fleet replies (`dashboard/osc_bridge.py:174`).
  Synced events come from dashboard UI surfaces (Devices, patch editor,
  control host) over websocket and from show playback, all via
  `OSCBridge.fire_event`. Quick search: "not found", not "proved absent".

Answer given: any app can send an `/e/*` event, but only the dashboard can
stamp one that fires synchronized. Outside apps effectively get `"0"`.

Follow-up done the same session: `docs/OSC-REFERENCE.md` gained an `/e/*`
section and lost its stale `/cue` rows (commit `4390fc3`).

## 3. Bob's node-side relative-lead idea

Bob asked whether the node could do the compensation: send "fire 500 ms
from the shared clock", with each device knowing its own offset.

Analysis given:

- Nodes already apply the offset; the dashboard only estimates it.
- **A relative lead needs an agreed starting instant.** "500 ms from now"
  means "from when the sender sent it", and no node can see that moment —
  only when its own copy arrived. Arrival times differ by network delay and
  jitter, so a relative lead collapses into "500 ms after my packet
  landed": the same spread as `"0"`, shifted later. The offset can't help;
  it describes the gap between clocks, not when the packet left.
- Subtracting each node's mean one-way delay would even out steady
  per-node differences but not per-packet jitter, which on Wi-Fi broadcast
  probably dominates (*inferred*). The only spread figure in the repo comes
  from the simulated baseline (`.loom/legacy-v1/tied/sync-3-jitter-harness/
  sync-baseline-report.md`: ~0.9 ms median with 2 ms injected jitter); no
  hardware `sync-4` result found.
- **Efficiency:** ~16 bytes per event saved; scheduling cost negligible
  either way. Sync traffic doesn't scale with events. The only real saving
  would come from dropping sync altogether.
- **The governing rule:** stamp the event with an absolute time at one
  point *before* fan-out. Delay before the stamp shifts every node equally;
  the lead absorbs delay after it.
- Two ways to admit outside senders were outlined: (1) a dashboard OSC
  ingress that stamps `now + event_lead_ms` and rebroadcasts; (2) a shared
  clock any app can read (NTP wall time / OSC bundle timetags), which runs
  against the contract's deliberate monotonic-clock choice (§3.1).

## 4. Belief System: what the large integer was

Bob recalled that Belief System (Happy Brackets on Pi Zeros, driven from
Ableton via Max for Live sending OSC) needed a large integer in its OSC
messages, with no dashboard doing clock maths, and still sounded well
synchronized indoors. Bob confirmed the relevant messages: sound
**objects**, the points moved around the space, which needed a
synchronized start time.

### Sources

- `~/repos/belief-control`, Bob's Max side:
  - `b14d02e` (2022-04-26) "added start time in millis to objectStart
    message".
  - Archived `archive/belief-control/particles.module.maxpat`:
    `cpuclock → % 9999999999999999 → o.pack /startTime`, packed into
    `/objectStart id voiceslot recording gain x y radius startTime rate`.
    Max's `cpuclock` counts milliseconds since the laptop booted.
  - Current `max/path.module.maxpat`: `cpuclock → % 25560 → /objectStart`
    argument 8.
  - Messages go as back-to-back unicast to each Pi on port 5555
    (`sub.UNICAST120`, `sub.targetsRouting`).
  - `conductor.module.maxpat` sends `/useTimeCorrection $1` from a "time
    correction" toggle.
- `Belief System tech bible 2.0.pdf` (22 Nov 2023), `/objectStart` spec:
  `start-time-in-millis` — "Unsigned int … n/a (modulo some big number) …
  A start time such as unix epoch in millis or system uptime."
- `orsjb/BeliefSystem` at `0de624b`, `BeliefSystemRenderer.java`, the Pi
  side. Ollie Bown's commit `67e6f3b` (2022-04-22): *"EXPERIMENTAL: I've
  added some time correction code. This requires bob to add an <int>
  timestamp arg to the end of the /objectStart message. … The idea is that
  we assume all messages are late, and we are tying to find the 'least
  late' message as an estimate of the real time."*

### The receiving code (excerpt, `BeliefSystemRenderer.java` at `0de624b`)

```java
@HBParam public int useTimeCorrection = 1;
...
long estimatedTimeZero = 0;
...
@HBCommand public void objectStart(int soundObjectID, int voiceSlot, int recordingID,
        float gain, float x, float y, float radius, int timestamp, float rate) {
    //deal with timestamp first
    long now = System.currentTimeMillis();
    long thisEstimatedTimeZero = now - timestamp;
    if(estimatedTimeZero == 0) {
        estimatedTimeZero = thisEstimatedTimeZero;
    }
    if(thisEstimatedTimeZero < estimatedTimeZero) {
        estimatedTimeZero = thisEstimatedTimeZero;
    }
    long offset = thisEstimatedTimeZero - estimatedTimeZero;
    ...
    if(useTimeCorrection == 0) {
        object.startTime = now;
    } else {
        object.startTime = now - offset;
    }
```

and in `swapObjects`, when an object becomes current on a speaker:

```java
//set the time so that the sample is in synch with other samples around it
float timeSinceStart = (float) (System.currentTimeMillis() - currentObject.startTime);
...
objectPlayer.setPosition((timeSinceStart * currentObject.rate) % selectedSample.getLength()); // LOOP
...
objectPlayer.setPosition(timeSinceStart * currentObject.rate);                                 // NO_LOOP
```

### Mechanism

1. Each Pi computes `now − timestamp` (its wall clock minus the laptop's
   `cpuclock`): clock difference plus this packet's network delay.
2. It keeps the minimum ever seen (`estimatedTimeZero`): the least-late
   packet as the best estimate of pure clock difference.
3. Each object's start gets backdated by that packet's excess delay over
   the fastest: `startTime = now − offset`.
4. When an object enters a speaker's radius, the sample starts at
   `timeSinceStart × rate` (wrapped for loops), so a speaker joining late
   lands in phase with its neighbours.

`/useTimeCorrection 0` switches step 3 off (raw arrival time). The renderer
makes no use of the Happy Brackets `Synchronizer` or scheduler: no
reference to either in `BeliefSystemRenderer.java`.

### Why it sounded tight (*inferred*)

- No leader, no round trips; the sender only stamps its own counter.
- Forgiving material: elapsed time sets the phase of looping textures that
  fade in and out (80 ms control clock, objects self-destruct after 5 s),
  not one-shot downbeats.

### Limits (*inferred* from code, untested)

- One-way timing can't separate network delay from clock difference: it
  removes only delay above each Pi's best case. A consistent per-Pi
  latency difference (sequential unicast bursts could produce one) stays
  as a phase error. bopOS's round trip (`RTT/2`) exists to remove that.
- The minimum never ages out: clock drift, NTP steps of
  `System.currentTimeMillis`, or a sender clock reset all degrade it until
  the renderer restarts. Daily reboots (`BS running notes.rtf`) would mask
  this.
- `cpuclock % 25560` wraps the sender clock every 25.56 s, giving apparent
  extra delays in multiples of 25,560 ms. That only stays harmless if loop
  lengths divide evenly into it; 25560 may have been chosen as a sample
  length. Speculative.

### Correction to earlier record

`2026-09-25-architecture-review-2026-07-05` §5 calls the Happy Brackets
Gen 1 `Synchronizer` "the one used for belief-era triggering" and the
appended long "the synchronised time at which to act". The code above
contradicts both for Belief System: the long carried the sender's own
uptime, and each Pi estimated a sender-clock mapping by minimum delay. The
review's description of Happy Brackets' library capabilities may still
hold; it just wasn't how Belief System used them.

## 5. Bob's conclusion (2026-10-11)

Ported to bopOS, the Belief System approach would let an outside app send
`<senderTimeMs> <leadMs>` with per-sender estimation on each node. Bob's
conclusion, close to verbatim: *"to implement that kind of timing, we
would still need some sort of clock in the sending application. Then
there's no real advantage. It's just as easy to allow the dashboard to
maintain timing and send messages via the dashboard, if we want to send
from an external application."*

Bob explicitly asked for no development to start. He asked for this record
in lore and the understanding in glean, so it holds going forward.

## 6. Open, not actioned

- A dashboard OSC ingress for outside senders: not designed, no stitch.
  Would need a contract amendment (Bob's to ratify).
- Hardware cross-device spread for bopOS `/e/*` (`sync-4`): no result found
  in the repo as of this session.
- `BeliefSystemRenderer`'s use of `% 25560` timestamps: unverified.
