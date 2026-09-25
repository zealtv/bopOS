# Wild ideas — the out-of-the-box annex

*Fable brainstorm, 2026-07-15. Unfiltered; each idea carries its own health
warning. Nothing here is roadmap.*

- **Seats as a sampler surface.** Invert the scatter: `hash(uid, seed)` gives
  every seat a stable random *personality* scalar per run. Scripts can use it
  as a free spatial random texture ("detune everyone by their personality") —
  zero wire cost, replayable, and it makes 30 identical Pis feel individual.

- **Fields modulating fields.** A field's *parameter* (e.g. a radial centre)
  driven by a point's position — the moving `/pt` point drags a gradient
  around the room. Composition of the two existing primitives, node-side,
  no new bandwidth. Probably one line in the field spec ("centre may bind to
  a point id") for a large expressive payoff.

- **The room as an oscilloscope.** The map-overlay renderer (§03) can run
  *from the wire*, not from intent — a debug mode that renders what the fleet
  was actually told (fields, points, recent cues as ripples). Rehearsal tool:
  see the show the network saw, spot the lost broadcast.

- **Automation recording.** Twist a dashboard slider while a clip records →
  breakpoints appear in a ramp clip (simplified on the fly). The cheapest
  possible "authoring by performing" loop, and it needs nothing but the
  existing internal API plus curve simplification (which the video baker
  needs anyway).

- **Clip provenance for the co-composer.** Since shows are text files, an
  agent can draft variations of a clip ("same gesture, sparser"). Keep a
  `variants/` convention next to clips so human and agent riffs accumulate
  as siblings, pickable from the inspector. The grid becomes a conversation.

- **Cue echoes / node-side rhythm.** A cue arg like `repeat 4 x 250ms` lets a
  node re-fire locally — a rhythmic figure per broadcast, not per note. This
  is the MIDI-note-stream killer for rhythmic material. (Contract-adjacent;
  really a "cue with args" question, which the manifest cue declarations
  already almost invite.)

- **Sensors close the loop later.** The io plane exists (`/io/*`); a
  future clip condition ("if room is loud, follow-action → other") turns the
  launcher from generative into *responsive*. Explicitly not now — but the
  follow-action model should keep a slot where a condition could live, which
  costs one field in the data model.

- **Show-level follow actions.** Follow actions between *scenes* (rows), not
  just clips: after scene A ×3 → random scene from {B, C}. This makes the
  whole installation a self-running graph — probably v1.5, it's the same
  state machine one level up.

- **The auxiliary rig as a seat.** Belief System's multichannel side system:
  give it a bopos.py of its own (or a simfleet-style stub) so it *is* a seat
  with an id, receives cues/params like everyone else, and needs no special
  casing anywhere. "Everything is a seat" is a unification worth testing
  against reality once, at least.
