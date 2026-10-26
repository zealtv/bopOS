# Synced events from outside apps go through the dashboard

When someone wants Ableton, Max, TouchOSC or another OSC app to send forward-synced `/e/*` events, the answer (Bob, 2026-10-11) is to route through the dashboard, which holds the clock — not node-side or sender-clock timing.

- **Shipped 2026-10-26 (contract v1.23):** send outside OSC to dashboard UDP **5552**. Only declared events/parameters are accepted, using the active fleet or edited-patch manifest. Send `/<target>[/e]/<identity> <fields…>` without a timestamp or sentinel: the dashboard stamps `monotonic_ns() + event_lead_ms`, or `"0"` at lead zero. Targets include group names. Defaults fill, numeric kinds coerce, out-of-range event fields clamp; errors/clamps enter a 50-entry runtime ring. All forwarding follows Live / Simulation / Patch Edit. `docs/OSC-REFERENCE.md` is the sender guide.
- **Direct node input still uses the device wire.** On 6660, outside apps must send `"0"` for unsynced fire-on-arrival; an arbitrary sender cannot know the dashboard's monotonic clock. Prefer 5552 for synchronized events.
- **A relative lead ("fire in 500 ms") doesn't sync.** Nodes can't see when a packet left, only when it arrived, so it collapses into fire-on-arrival plus a delay. Stamp an absolute time at one point *before* fan-out.
- **Sender-clock timing was considered and set aside.** Belief System had each Pi estimate the sender's clock from the "least late" message. Bob's call: it still needs a clock in the sending app, so it has no real advantage over letting the dashboard keep timing.

- **Belief System didn't use the Happy Brackets synchronizer.** Its large `/objectStart` integer carried Max's `cpuclock`. The 2026-09-25 architecture review §5 says otherwise; the code contradicts it.

## Context

Full record, code excerpts and limits: lore `2026-10-11-external-osc-sender-timing`.

## Triggers

- Belief System
- Happy Brackets
- HappyBrackets
- Ableton
- TouchOSC
- external OSC
- sharedTimeNs
- objectStart
- relative lead

## Associations

- [[osc-contract]]
- [[decision-gates]]
- [[pd-float-precision]]
