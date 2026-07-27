# 1-event-plane-design

Design the **event** wire plane and the explicit `kind` grammar. Written
proposal, **Bob ratifies** (contract amendment), tie with `decisions.md`;
implementation children follow.

Read the parent `instructions.md` first — it carries six rulings Bob made on
2026-07-27 that close most of what this stitch originally had to ask. In
particular: every event forward-syncs (no per-row `sync` button; global lead
time `0` *is* sync-off), cues are zero-element events and `/cue` is deleted
outright, the manifest moves to an explicit `kind` field as a hard break,
event elements are free-form labeled floats, presets don't capture events,
and no automation is designed. **Do not re-open any of those.**

Sources: mockup panel 3 shows the intended rows — `64.0 event[1]`,
`64.0 127.0 event[2]`, `64.0 127.0 2000.0 event[3]` (drop the `sync` button
the mockup draws beside each; keep the fire button).

## What the proposal must answer

1. **The `kind` grammar.** The declaration shape for `toggle`, `integer`,
   `enum`, and `event`, replacing today's `type: i|f|s` plus `options`. What
   `kind` values exist, what fields each one carries, and what happens to
   `type` (gone, or retained as the wire encoding beneath `kind`?). String
   params (`s`) exist in the current grammar — say where they land. Because
   this is a hard break, spell out the sweep: `python/manifest.py`
   (`PARAM_TYPES`, the `options` validation, the `events` block),
   `dashboard/show_model.py` (which reuses `PARAM_TYPES` verbatim), the patch
   editor's declaration UI, saves/round-tripping, and every fixture manifest
   in `tests/`.
2. **The plane.** Address (`<target>/e/*` is Bob's guess) and its row in the
   §3 planes table. Events are *patch-declared* like `/p/*` but
   *framework-synchronized* like the old `/cue`, which is the interesting
   part: the framework has to intercept and schedule a patch-declared address.
   Say how that reads in the planes table and how an undeclared event address
   is handled (the `/p/*` precedent is "a badge, not a guess").
3. **Wire shape for arity 0–3.** How a fired event serializes, all the way
   from a surface through `bopos.py` to the engine, including the zero-element
   (cue) case. Engines must only ever see **relative** time (§3.1, PD float
   discipline — no absolute epochs, no >6-significant-figure floats).
4. **Forward synchronization.** How the event fire inherits §3.1's
   `cue_lead_ms` / shared-time machinery instead of opening a second clock
   path. Specify the lead-time-`0` degenerate case explicitly — it is the only
   sync-off switch, so it has to be exactly equivalent to firing immediately.
5. **The `/cue` deletion sweep.** Enumerate what gets removed and what each
   call site becomes: contract §3.1 and §8 (`cues` manifest key), `bopos.py`
   cue scheduling, the engine receiver, simfleet, audition, relay, Show-tab
   cue steps and their persistence (existing `dashboard/shows/*.json` need a
   migration answer), Control-tab cue triggers. Old handling is **deleted, not
   deprecated**.
6. **Show / pill integration.** Message kinds for the Show tab, and how the
   ratified flat eight-category pill set (tied `25-message-pill-encoding`)
   changes when the `cue` category's subject becomes a zero-element event —
   does `cue` survive as a pill name, or does an `event` category replace it?
7. **Parity.** Engine (`bopos~`/template — **Bob owns `.pd` edits**; write the
   needed receiver changes into `.notes/pd-edits-for-bob.md`, don't edit
   `.pd`), simfleet, audition, relay, and the editor surface. Name which of
   these can be verified headlessly and which need the rig.

One sentence, no more, naming the future door: event-specific automation is
expected eventually but its shape is unknown and out of scope.

## Not in scope

Toggles, integers, and enums — they already ship. Preset capture of events —
ruled out. Automation of events — not designed. The control panel's UI shape
for event rows — that is
`desktop-ui-overhaul/01-control-panel/2-control-panel-design`; this stitch only
tells it that there is one fire button, not two.

Mark `.waiting` for Bob's ratification when the proposal is written.
