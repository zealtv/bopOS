# Decisions — 06-application-core

Date: 2026-07-29.

## One application path

`Dashboard.apply_preset(patch, name, scope, target_id, duration_ms=None,
curve=None)` is the server-side application boundary. The `apply_preset`
WebSocket mutation is serialized by the existing supervisor lock and delegates
straight to it; later Control, Device, editor, and Show callers do not get
separate application logic. The old venue-state `load_preset` remains unchanged
until its explicitly sequenced retirement in stitch 10.

The service loads through `PresetStore`, resolves the requested scope to Seats,
filters those Seats by effective patch (bound Device pin, else fleet patch),
then resolves drift through the store's pure resolver. A patch mismatch is a
non-blocking per-Seat `skipped` result and never receives a parameter message.

Apply takes a memory snapshot, records every durable/automation/provenance
change without sending, and calls `InstallationState.save()` once. A failed
save restores all seat, device, automation, and provenance mirrors and sends
nothing. After a successful save it emits the prepared OSC messages and one
`preset_applied` application report.

## Selector coalescing

`all` and `gN` are retained only as a send optimization when every concretely
resolved Seat survives patch filtering. If any Seat is skipped, the service
fans out to numeric Seat selectors.

This optimization has two accepted named deltas and is not represented as
strict equivalence:

- `all` also matches unassigned Devices, while numeric Seat fan-out cannot;
- a `gN` datagram can observe transient node membership-sync lag.

Both match existing all/group control behavior. The code comment at the
coalescing branch records the same boundary.

## Timed apply and canonical state

With a duration, scalar `float` and `int` entries use the existing fade form
`[destination, duration, c:n?]`. Generator, toggle, enum, and text entries send
their full state immediately and increment `snapped`. In particular, enum
indices never traverse the integer fade path. Without a duration every entry
is an ordinary full-state send.

`preset_application.canonicalize_value/args` is the shared boundary used by
apply, capture, dirty comparison, and the existing live scalar/automation
write paths. Floats are reduced with the OSC datagram's `.6g` rule and integer
durable destinations are floored, so dashboard mirrors hold what was sent.

## Automation, replay, and Stop

`OSCBridge.record_param` separates mirror recording from transport. Ordinary
`set_param` retains its existing persistence/broadcast behavior; preset apply
uses the non-persisting form to batch one transaction.

Replay derives activity rather than removing completed entries:

- LFO and loop entries are always active and replay verbatim;
- a fade is active only before `sent_at + total duration`;
- an expired fade replays the canonical durable destination.

Replay sends directly and never rewrites `sent_at`, so an almost-finished fade
is not resurrected in dashboard state.

Stop remains `stop` on the wire. Before sending it, the dashboard evaluates the
generator at stop time and stores that canonical estimate durably. Synced
periodic shapes and fades are deterministic from the recorded state.
Free-running LFOs and `sh`/`drift` remain documented dashboard estimates
because device-local phase/output is unknowable; using a plain set instead
would collapse legitimately divergent Devices.

## Provenance, capture, and dirtiness

Each concrete Seat carries runtime-only `applied_preset {patch, name}` and
derived `preset_dirty`. `InstallationState.durable()` explicitly removes both,
so restart forgets provenance just as it forgets automation. A new apply
overwrites the matching Seats; recall-none clears them. Skipped Seats retain
their prior provenance.

Capture reads intended dashboard state: active LFO/loop args verbatim, otherwise
the canonical durable scalar (therefore a fade destination), and omits any
identity whose target Seats disagree. Events are absent by construction because
only manifest parameter declarations are projected. Exact target sets project
to `all`, then an equal group membership, then a Seat list; identical groups
choose the lowest numeric group id.

Card projection uses the established agree-or-mixed rule. Dirty state is
derived server-side from the cached preset body against canonical durable
values and active generator args; clients receive only per-Seat provenance and
the boolean, never preset bodies.
