# 1-event-plane-design

Design the event parameter kind and its wire plane. Written proposal, **Bob
ratifies** (contract amendment), tie with `decisions.md`; implementation
children follow. Source: the 2026-07-27 braindump (lore
`2026-07-27-control-panel-ui-and-architecture-braindump`) — mockup panel 3
shows the intended UI: event rows `64.0 event[1]`, `64.0 127.0 event[2]`,
`64.0 127.0 2000.0 event[3]`, each with `sync` and `send` buttons — plus the
same-day widening (lore
`2026-07-27-events-cues-and-global-controls-braindump`): **a cue is an event
with zero elements**, and cues may be absorbed into the event plane
entirely.

## What the proposal must answer

1. **Kinds and declaration.** Manifest shape for toggles, integers, enums,
   and events (arity 1/2/3, per-element ranges/semantics — typically MIDI
   note/velocity/duration-ms). How enums declare their symbol set. What of
   this is new manifest `type` values vs a new `kind` field; migration for
   the existing `i/f/s` scalar grammar and validator.
2. **The plane — cue absorption is RULED.** Bob (2026-07-27): **cues are
   absorbed into the event plane as a hard break.** A cue is a zero-element
   event; the `/cue` plane goes away in the same contract revision, with no
   compatibility shim or legacy path — no production shows rely on cues, so
   keep the code clean. What remains to design: the plane address
   (`<target>/e/*` is Bob's guess) and its place in the §3 planes table
   (events are *patch-declared* like `/p/*` but *framework-synchronized*
   like the old `/cue`); the wire shape for arity 0–3; and the migration
   sweep — manifest-declared cues, Show-tab cue steps and pill taxonomy,
   Control-tab cue triggers, engine/simfleet/audition/relay — all move to
   zero-element events, old `/cue` handling deleted, not deprecated.
   Engines must only ever see relative time (PD float discipline: no
   absolute epochs, §3.1).
3. **Forward synchronization.** Wire shape for a synchronized event: lead
   time, shared-time reference, per-node local firing — the §3.1 cue
   machinery (`cue_lead_ms`, shared_time) is *inherited by* the event plane
   (cues are now events), not duplicated as a second clock path. What
   "sync" vs "send" (immediate) means per the mockup buttons.
4. **Automation interaction.** Bob: integers/enums "we'd need to consider
   what, if any, automation is applicable". Events presumably don't take
   §3.2 generators — but a *pattern/repeat* affordance may be wanted later;
   name the door, don't design it.
5. **Preset capture.** What a preset stores for a toggle/int/enum (a value)
   and for an event param (probably its last-sent tuple? or nothing —
   events are momentary). This feeds 41 directly; recommend, and flag the
   choice to Bob.
6. **Show/pill integration.** Message kinds for the Show tab and how the
   ratified flat eight-category pill set extends (coordinate with the tied
   `25-message-pill-encoding` taxonomy).
7. **Parity.** Engine (`bopos~`/template — Bob owns `.pd` edits, note them
   in `.notes/pd-edits-for-bob.md`), simfleet, audition, relay, and the
   editor surface.

UI ruling already made (don't re-litigate): the control panel gets a
**parameters section and an events section**, not intermingled; cues (as
zero-element events) live in the events section with all/group/seat
targeting. Panel order follows manifest order (drag-reorder is
`desktop-ui-overhaul/01-control-panel/8-manifest-reorder`).

Keep the scalar kinds (toggle/int/enum) cheap — they may be pure
manifest/UI work on the existing `/p/*` plane — and let events carry the
design weight. Mark `.waiting` for Bob's ratification when the proposal is
written.
