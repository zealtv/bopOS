# clock-sync

**Goal:** a forward-synchronised clock across all bopOS devices so cues can be triggered
sample-tight(ish) over WiFi, engine-agnostically.

Reference design: `.notes/architecture-review-2026-07-05.md` §5 (Happy Brackets
`Synchronizer` / `HBScheduler`, read from source — the belief installation used this).

Mechanism (HB-style, adapted):
1. Leader (the dashboard backend) broadcasts a ping: `/sync/ping <seq> <leaderTime>`.
2. Each Pi's **helper.py** replies unicast: `/sync/pong <seq> <leaderTime> <mac> <myTime>`.
3. Leader computes per-device offset: `oneWay = roundTrip/2`,
   `offset = (deviceTime + oneWay) - leaderNow`; smooths over many rounds; pushes the
   correction to the device (or device computes its own — pick one side and document it).
4. Cue: `/cue <cueId> <sharedTime>`; helper.py converts sharedTime → local monotonic
   deadline, then at the deadline fires `/cue <cueId>` to the engine on localhost.

Hard constraints (learned from HB + PD):
- **PD never sees an absolute timestamp** — 32-bit OSC floats mangle epoch millis. Encode
  64-bit times as strings or two ints on the wire; PD only receives the bare cue at
  fire-time (or a small relative delay).
- Use `time.monotonic()` on the Pi, never wall clock (NTP steps would glitch cues).
- **Slew** corrections while audio runs (HB gen-2: `adjustScheduleTime(amount, duration)`),
  never step.
- Randomise ping intervals slightly to avoid lockstep network bursts (HB does 500±100 ms).

Decisions:
- **RESOLVED (Bob, 2026-07-05): the dashboard backend is the clock leader.** Tight-sync
  features may assume the dashboard is running; Pis stay autonomous for everything
  else. No leaderless MAC-election needed.
- Still open (implementer's call, record it): where the offset math lives
  (leader-side vs device-side).
- Expected accuracy target: HB achieved musically-usable sync on WiFi with this; measure
  actual jitter on our network before over-engineering (a test harness that flashes a
  GPIO/click on N Pis and records them together is the honest measurement).

Done when: N Pis on WiFi fire an audible click cue within an agreed jitter budget
(target: <10 ms typical), demonstrated with a recorded measurement.
