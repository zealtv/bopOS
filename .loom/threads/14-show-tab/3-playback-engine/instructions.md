# 3-playback-engine

The transport: an asyncio playback engine in the dashboard backend driving
steps and emitting OSC through the existing relay path. Requires stitches
1 and 2.

Scope:

- Separable module (e.g. `dashboard/show_engine.py`) consuming the stitch-2
  model; talks to the fleet only through the same internal send path the
  tabs use (see how live controls / cue triggers send today). No new LAN
  sockets.
- Per-step state machine per the design note: start (fires the step's
  messages together, begins duration), stop, pause/resume, "trigger next
  action now". Duration expiry after play-n-times iterations resolves
  then-actions: stop, play again, next/previous step, any/other in section
  (seeded RNG acceptable; `other` is a per-section shuffle-bag), goto,
  next/previous section (lands on the first step of the target section).
  Multiple then-actions → uniform random pick.
- Playback state (which steps are playing/paused, iteration count,
  remaining time) broadcast to WS clients on change and on connect.
- Forward-sync flag: flagged steps' messages use the existing clock-sync
  scheduled/cue-plane delivery where the message kind supports it; others
  send immediately. Respect PD float precision law.
- Global stop-all command.

Verify: `verify_show_engine.py`, headless against simfleet on non-default
ports — assert simfleet receives the right OSC for: a step firing its
message set together, play-n-times looping, next/goto chains, `any`/`other`
staying within the section with `other` exhausting before repeating,
multi-then randomness (seed or statistical), pause freezing the countdown,
stop-all, and a forward-synced step arriving via the scheduled path.
