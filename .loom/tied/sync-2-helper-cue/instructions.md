# sync-2-helper-cue

Device side in helper.py: answer sync pings, hold the correction, fire cues.
Mechanism in `../instructions.md`; wire shape from sync-0; leader/device split
decided in sync-1 — read its notes first.

- [x] Pong handler: `/sync/pong <seq> <leaderTime> <uid> <deviceTimeNs>` unicast
      to the pinger on 5550, `deviceTime = monotonic_ns()` (never wall clock).
- [x] `sync_node.SyncState` holds the correction and **slews** toward each
      pushed target over ~1 s (lazy interpolation), never steps.
- [x] `/cue` → `sync_node.CueScheduler` converts to a local monotonic deadline
      (`sharedTime + offset`) and fires the **bare** `/cue <cueId>` to PD on 6661.
- [x] Late-cue policy: fire if within a 50 ms grace, else drop; both logged.
      Rationale in `results.md`.
- [x] simfleet unchanged since sync-0 (no wire shift).
- [x] `verify_sync_helper.py`: sync_node unit checks + real helper.py loopback
      (ping→pong, offset push, cue 400 ms out fires bare `/cue` to 6661 within
      ~0.1 ms). Results in `results.md`.

Note (flagged for Bob, in `results.md` + handoff): PD needs a `/cue` receiver on
6661 — a pd-edits item, not an agent edit.

Real-hardware verification belongs to sync-4, not here — don't claim it.
