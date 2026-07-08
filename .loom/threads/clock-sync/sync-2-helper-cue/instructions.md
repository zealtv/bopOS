# sync-2-helper-cue

Device side in helper.py: answer sync pings, hold the correction, fire cues.
Mechanism in `../instructions.md`; wire shape from sync-0; leader/device split
decided in sync-1 — read its notes first.

- [ ] Pong handler: reply unicast to the pinger with `<seq> <leaderTime> <uid>
      <deviceTime>` using `time.monotonic()` — never wall clock.
- [ ] Hold the shared-time correction; **slew** adjustments (HB
      `adjustScheduleTime(amount, duration)`-style), never step while running.
- [ ] `/cue <cueId> <sharedTime>` → convert to local monotonic deadline → at
      deadline send bare `/cue <cueId>` (or small relative ms) to the engine on
      localhost. **PD never sees absolute time** (house rule).
- [ ] Late-cue policy (deadline already passed): fire-immediately vs drop —
      implementer's call, record it, make it observable (log line).
- [ ] simfleet stays protocol-identical if anything shifted since sync-0.
- [ ] verify_*.py: leader + simfleet + one real helper.py instance on loopback;
      cue scheduled 500 ms out fires within a loopback-tight bound.

Real-hardware verification belongs to sync-4, not here — don't claim it.
