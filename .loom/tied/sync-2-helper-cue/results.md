# sync-2 — node side (helper.py + sync_node.py): results

The device half of the clock-sync plane (`sync-0` wire shape, `sync-1` leader).
All Python; no `.pd` edits (one PD receiver is flagged for Bob below).

## What landed

- **`python/sync_node.py`** (new) — the node-side timing, deliberately free of
  import-time side effects so it unit-tests without binding helper's ports:
  - `SyncState` — holds the working offset and **slews** toward each pushed
    target over ~1 s (lazy interpolation; no extra thread), so a correction
    never steps live audio. `offset()` = current working value;
    `offset ≡ deviceClock − leaderClock`.
  - `CueScheduler` — a thread that fires each cue at `sharedTime + offset()` on
    the local monotonic clock, re-reading the offset every wakeup (≤20 ms cap)
    so a slewing correction is tracked to the deadline.
- **`python/helper.py`** — wired in:
  - `/sync/ping` → `/sync/pong <seq> <leaderTime> <uid> <deviceTimeNs>` unicast
    to the leader on 5550, `deviceTime = monotonic_ns()` (never wall clock).
  - `/<id>/sync/offset` (selector-matched) → `sync_state.push(offset)`.
  - `/cue <cueId> <sharedTimeNs>` → `cue_scheduler.schedule(...)`; at the local
    deadline `fire_cue_to_engine` sends the **bare** `/cue <cueId>` to PD on
    6661 — absolute time never enters the engine (contract §12).
  - Handled before the existing `/os` gate in `handle_lan_datagram`; scheduler
    thread started in `__main__`.

## Implementer's call — late-cue policy (recorded here)

A cue whose deadline has already passed when the scheduler reaches it is **fired
if within a 50 ms grace window, otherwise dropped** (`CUE_LATE_GRACE_NS`). Both
outcomes log a line (`cue <id> fired (late …)` / `cue <id> DROPPED (late … >
grace)`). Rationale: a small network/scheduling hiccup shouldn't silently drop a
downbeat, but a cue arriving long after its moment is stale — firing it late is
worse than not firing (it lands audibly wrong and out of sync with the fleet).
50 ms ≈ perceptible-attack threshold and comfortably above loopback/LAN
scheduling noise; revisit against `sync-3`'s measured jitter.

## Consistency with sync-1

`offset ≡ deviceClock − leaderClock` and `deadline = sharedTime + offset` match
the leader's estimate and push exactly. The node only ever receives the absolute
offset (full-state, idempotent) and slews internally — no deltas on the wire.

## Verify — `verify_sync_helper.py` (browser- and hardware-free)

```sh
pip install pyOSC3
python3 verify_sync_helper.py     # from this stitch dir; locates repo by marker
```

Part A unit-tests `sync_node` (slew ramp + continuity on an injected clock;
CueScheduler on-time/grace/stale firing on the real clock). Part B imports the
**real** `helper.py` and drives `handle_lan_datagram` on loopback: a ping gets a
well-formed pong, an offset is applied, and a `/cue` 400 ms out fires the bare
`/cue c1` to the engine socket on 6661 within ~0.1 ms of its deadline. Stable
across 3 runs (2026-07-09).

## Flag for Bob — one PD receiver (not an agent edit)

The engine now receives a bare `/cue <cueId>` on 6661 at fire time. The default
patch needs a `[/cue]` receiver that maps a cueId to whatever it triggers —
**PD is Bob's domain**, so this is a pd-edits item, not done here. Until it
exists the cue lands harmlessly (no receiver). Add to the running PD-edits list
alongside the `level` meter item; noted in the session handoff.

## Not verified here (needs hardware — sync-4)

Real PD firing, real Pi clocks, and GPIO/click-recorded cross-device jitter are
`sync-4` (hardware, `.waiting`) and `sync-3` (jitter harness). This stitch
proves the wire glue and the timing logic on loopback only — no hardware claim.
