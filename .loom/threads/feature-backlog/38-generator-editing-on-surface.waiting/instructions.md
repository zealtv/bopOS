# 38-generator-editing-on-surface (feature backlog)

Per-parameter generator editing (choose an LFO, set rate/depth, etc.) directly
on the shared control surface — not only via the Show inspector's message
builder. The `automation-2` generator-builder GUI already compiles to the §3.2
wire grammar; extract/reuse it rather than duplicating.

## Pushed to someday-later (Bob, 2026-07-24)

Marked `.waiting` — a someday-later task, not queued behind the current sweep.
Resume only on an explicit Bob call.

## Deferred here by Bob, 2026-07-24

Parked while thread `37-device-scoped-patch-control` takes its first clean bite
(device-scoped patch targeting + drift badge + fleet-patch mirror). Deferral
changes priority only; it does not drop or narrow the work. This was originally
folded into the widened `37/1-device-patch-control-design` scope
(lore `2026-07-24-patching-session-braindump`); it comes back with the shared
control-surface restructure, and what a generator means *inside a preset*
remains thread `41-preset-primitive`'s design.
