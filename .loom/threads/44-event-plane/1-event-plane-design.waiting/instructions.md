# 1-event-plane-design

Design the event parameter kind and its wire plane. Written proposal, **Bob
ratifies** (contract amendment), tie with `decisions.md`; implementation
children follow. Source: the 2026-07-27 braindump (lore
`2026-07-27-control-panel-ui-and-architecture-braindump`) — mockup panel 3
shows the intended UI: event rows `64.0 event[1]`, `64.0 127.0 event[2]`,
`64.0 127.0 2000.0 event[3]`, each with `sync` and `send` buttons.

## What the proposal must answer

1. **Kinds and declaration.** Manifest shape for toggles, integers, enums,
   and events (arity 1/2/3, per-element ranges/semantics — typically MIDI
   note/velocity/duration-ms). How enums declare their symbol set. What of
   this is new manifest `type` values vs a new `kind` field; migration for
   the existing `i/f/s` scalar grammar and validator.
2. **The plane.** Is `<target>/e/*` a new framework plane (Bob's guess) or
   an extension of `/p/*`? The §3 planes table is closed — argue the
   boundary: events are *patch-declared* (like `/p/*`) but *framework-
   synchronized* (like `/cue`). Whichever side wins, engines must only ever
   see relative time (PD float discipline: no absolute epochs, §3.1).
3. **Forward synchronization.** Wire shape for a synchronized event: lead
   time, shared-time reference, per-node local firing — reuse the §3.1
   cue machinery (`cue_lead_ms`, shared_time) rather than a second clock
   path. What "sync" vs "send" (immediate) means per the mockup buttons.
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

Keep the scalar kinds (toggle/int/enum) cheap — they may be pure
manifest/UI work on the existing `/p/*` plane — and let events carry the
design weight. Mark `.waiting` for Bob's ratification when the proposal is
written.
