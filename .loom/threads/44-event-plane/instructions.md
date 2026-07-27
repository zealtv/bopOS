# 44-event-plane

Event-type parameters and their wire plane, from Bob's 2026-07-27 mockup
braindump (lore `2026-07-27-control-panel-ui-and-architecture-braindump`,
re-emphasized by Bob same day): beyond floats the system needs **toggles,
integers, enumerators** (wire as integer; automation applicability TBD) and
**events** — single floats, float pairs (MIDI note + velocity), and triplets
(note + velocity + duration) — "specced out carefully", with **forward
synchronization** ("so these are probably a new plane ie `<target>/e/*`").

**Widened same day** (lore `2026-07-27-events-cues-and-global-controls-braindump`):
**a cue is an event with zero elements.** **RULED (Bob, 2026-07-27, same
session): cues ARE absorbed into the event plane, as a hard break.** No
production shows rely on the existing `/cue` machinery, so the OSC schema
changes cleanly — no compatibility shim, no legacy `/cue` path retained;
keep the code clean. Existing cue surfaces (manifest-declared cues, Show-tab
cue steps, Control-tab cue triggers) migrate to zero-element events in the
same sweep. Cue triggering moves onto the control panel, targetable at all
seats / a group / an individual seat; the control panel gains separate
**parameters** and **events** sections (no intermingling for now — keeps the
manifest construction area less changed). Cue lead time remains a single
global control (see the global-controls relocation in
`desktop-ui-overhaul/03-global-controls-monitor`).

Bob's sequencing call (2026-07-27): this "might be something that needs to
be implemented before the preset design" — so this thread is **queued ahead
of `41-preset-primitive`**, and 41's design must treat event-kind params as
in-scope for what a preset can capture (or explicitly rule them out with
Bob).

Anything wire-visible is an OSC-contract amendment (a new plane is a §3
Planes-table change — the framework plane set is closed, so this is a
ratified revision, not an addition by convention). Coordinate with:

- the §3.1 sync/cue plane — forward-synchronized events should reuse its
  shared-time machinery and the engine's relative-ms discipline, not invent
  a second clock path;
- the §3.2 automation grammar — Bob asks what, if any, automation applies
  to integers/enums, and events may interact with generators differently;
- the manifest (§8) — event params need a declaration shape (kind, arity,
  ranges) so surfaces can render them; today's `PARAM_TYPES` is `i/f/s`
  scalars only;
- `desktop-ui-overhaul/01-control-panel/2-control-panel-design`, which specs
  the *UI* shape for these kinds (sync + send buttons per event row in the
  mockup) — the UI stitch describes, this thread ratifies the wire and
  implements engine/simfleet/relay parity.

Start with `1-event-plane-design` (Bob-gated proposal); implementation
stitches follow ratification.
