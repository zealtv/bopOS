# 1-preset-architecture-design

Design the preset primitive. Written proposal, **Bob ratifies**, tie with
`decisions.md`; then child implementation stitches. Source: lore
`2026-07-24-patching-session-braindump` plus Bob's same-day extension
(Show-tab triggering + interpolation).

## What Bob has said (input, not yet ratified as a design)

- A preset is **defined by a patch's manifest** and applies to a single
  device/seat. Collections of presets then apply to groups/seats/all.
- Save-from-the-editor: while editing a patch with its control panel open,
  "save preset" captures the current state.
- Load-from-the-Control-tab: pick a seat/group/all and apply.
- **Show-tab triggering**: a show step can apply a preset to targets — and
  optionally **interpolate** into it with a duration + curve, morphing the
  current state into the preset rather than snapping.
- "I think we need to look at those approaches and find the best
  architectural solution for what a preset should be."

## Bob's 2026-07-24 extension: generators live in presets

Bob, same day, in conversation (his words: "it is clear the best workflow
would allow generator editing at the control surface level. choose an lfo,
rate, depth etc from the interface. that gets saved with the preset.
interpolation between generators is a mix function."):

- **Generator editing belongs on the control surface.** Pick an LFO, set
  rate/depth etc. per param, directly from the interface — not only from
  the Show inspector's message builder. (The Show-tab generator builder GUI
  from `automation-2` already compiles to the wire grammar — reuse/extract
  it, don't build a second one. Feeds thread 37's surface design: each
  param control needs a generator affordance.)
- **A preset captures generator state**, not just instantaneous values.
  Per param, a preset entry is either a static value or a generator spec
  (kind + args). This largely answers the old Q4 "what does a preset
  capture when a generator is running" — the generator itself.
- **Interpolation between presets involving generators.** Bob's first
  framing: "interpolation between generators is a mix function" —
  crossfade each param between its A-source and B-source outputs, which
  implies two sources per param plus a ramped mix coefficient (a §3.2
  amendment and engine work). But Bob added, same conversation: **"if
  there is a more elegant approach I might prefer it."** So the mix
  function is a candidate, not the ratified mechanism. The proposal must
  compare at least:
  1. **Output crossfade (the mix function)** — general, handles any
     source pair, but doubles per-param sources in the engine and is the
     biggest contract/DSP change; assess Pi Zero-class cost.
  2. **Generator-arg interpolation** — generator args (rate, depth,
     center…) are themselves fadeable: a same-kind transition (LFO→LFO)
     morphs the *running generator's parameters* over duration+curve, one
     slot per param preserved, and the fade concept is reused recursively
     rather than a new mixing primitive. Kind-changing transitions need a
     rule — e.g. ramp outgoing depth→0 onto the incoming center, swap
     kinds, ramp incoming depth up — which may be *musically* better than
     a raw output crossfade anyway (no phase-clash artifacts).
  3. Anything else that falls out of the grammar review.
  Recommend one, with the wire-shape delta for each considered.
  Static→static remains today's `param-fade` in every variant.

## Ruled by Bob, 2026-07-24: individual targetability + hard takeover

"Parameters should remain individually targetable from the show, control
tab, or anywhere else. Hard takeover might be the simplest global
approach." Consequences the proposal builds on, not re-litigates:

- **A preset is not a layer, lock, or ownership claim.** Applying one is a
  fan-out of ordinary per-param messages; afterwards each param is exactly
  as grabbable as before. Any later message to an individual param — from
  the Show tab, Control tab, anywhere — simply takes over that param,
  including **mid-interpolation** (a direct set during a preset morph wins
  on that param; the rest of the morph continues unaffected).
- This extends today's §3.2 take-over semantics to the global model rather
  than inventing a second ownership scheme. It also weighs against the
  two-source mix engine (which flirts with layered ownership) and toward
  per-param mechanisms that keep one slot, one owner, last-writer-wins.
- The proposal may still argue for something richer if hard takeover
  proves musically insufficient somewhere — but the burden of proof is on
  the richer scheme, and per-param individual targetability is
  non-negotiable.

**Also ruled (Bob, 2026-07-24): storage — presets travel with the patch;
shows do not.**

- **Presets live in the patch folder** (e.g. a `presets/` beside the
  manifest): strictly 1:1 with the manifest, versioned and distributed
  with the patch through the existing fetch machinery, dead with the patch
  if it's deleted. This settles the Q1 storage fork (patch-side, not
  dashboard-side) and the Q7 save destination (the editor's "save preset"
  writes into the patch folder). Q1's remaining live part is the
  **manifest-drift policy** (what happens to saved presets when the
  manifest changes under them).
- **Shows stay composition-level** (`dashboard/shows/` is the canonical
  home, now versioned): a show is potentially 1:N over patches (37's
  per-device direction), carries composition material no manifest defines,
  and must survive patch deletion. Instead of containment, the **show
  document records the patch name(s) + fingerprint(s) it was authored
  against** — reuse the same drift-detection mechanism presets need, so
  the dashboard can warn on mismatch. A patch **may bundle** a demo show
  as an *import source* (matches the "demos live in `patches/`" ruling):
  opening the patch offers a copy into `dashboard/shows/`; the copy is the
  live document. The proposal designs the fingerprint-reference field and
  the drift warning; it does not revisit where things live.

## Questions the proposal must answer

1. **Identity & storage.** *Ruled (see above): patch-side, in the patch
   folder.* Remaining: the manifest-drift policy — what survives a patch
   edit (partial apply on drift, or a fingerprint-mismatch rule?).
2. **Shape.** Named map over the manifest's numeric `/p/*` params where
   each entry is a static value **or a generator spec** (per the
   2026-07-24 extension). What about params a preset deliberately omits
   (sparse presets)?
   Non-numeric/manifest-kind gaps stay out of scope (strings/mixed arrays
   are still an undecided manifest kind).
3. **Application path.** Recommend replaying through the existing
   selector/targeting machinery (a preset apply = a fan-out of `/p/*`
   sets on a selector list) — reuse, don't fork. Confirm or refute.
4. **Interpolation.** Per the 2026-07-24 extension above: value→value is
   today's `param-fade`; generator-involved transitions need a mechanism —
   compare the output-crossfade mix function against generator-arg
   interpolation (and any third option), per the criteria in the
   extension section. Design the wire shape, engine/simfleet
   implementation, curve-vocabulary reuse, and interaction with existing
   take-over semantics (a plain non-interpolated apply is presumably
   still take-over).
5. **Collections.** What is a collection on the wire and on disk — a
   selector→preset map? Where does it live (it spans patches or targets,
   so it may not belong to one manifest)?
6. **Show integration.** Message/action kind for the Show document model
   (a new then-action, or a message kind alongside param-fade?); how the
   pill encoding taxonomy extends (coordinate with the ratified flat
   eight-category set from `25-message-pill-encoding`).
7. **Editor save flow.** *Destination ruled: the patch folder.* Remaining:
   whether presets sync to nodes at all (they ride patch distribution
   anyway) or apply stays purely dashboard-driven fan-out.
8. **Migration.** What happens to today's dashboard-side presets (the
   empty-preset cleanup already happened; is there anything worth
   migrating, or retire them?).

## Coordination

- **Thread 37** (`37-device-scoped-patch-control/1`) designs the shared
  control-surface component and Control tab that *hosts* the preset UI —
  sequence this design after or alongside it; the save/load affordances
  live on that surface.
- **OSC contract**: anything wire-visible is a contract amendment —
  propose the delta, don't implement past ratification.
- Show-tab actions coordinate with the tied Show document model and the
  Bob-gated `scene-sequencing` boundary: preset-trigger-with-duration is
  authorized input here, but don't wander into lanes/scenes design.
