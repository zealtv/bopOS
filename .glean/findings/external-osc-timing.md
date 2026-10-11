# Synced events from outside apps go through the dashboard

When someone wants Ableton, Max, TouchOSC or another OSC app to send forward-synced `/e/*` events, the answer (Bob, 2026-10-11) is to route through the dashboard, which holds the clock — not node-side or sender-clock timing.

- **As of 2026-10-11, only the dashboard can stamp a synced event.** Nodes accept `/e/*` from anyone, but `sharedTimeNs` is the dashboard's own `monotonic_ns()` plus the lead; an outside app can't know that clock. A guessed time more than 50 ms late gets dropped; a far-future one waits. Outside apps should send `"0"` (fire on arrival, unsynced). `docs/OSC-REFERENCE.md` documents this.
- **A relative lead ("fire in 500 ms") doesn't sync.** Nodes can't see when a packet left, only when it arrived, so it collapses into fire-on-arrival plus a delay. Stamp an absolute time at one point *before* fan-out.
- **Sender-clock timing was considered and set aside.** Belief System had each Pi estimate the sender's clock from the "least late" message. Bob's call: it still needs a clock in the sending app, so it has no real advantage over letting the dashboard keep timing.
- **Future path, not started:** a dashboard OSC input that takes outside events and stamps `now + event_lead_ms`. A contract amendment, Bob's to ratify; Bob asked for no development on 2026-10-11.
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
