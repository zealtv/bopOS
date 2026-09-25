# Sequencer brainstorm — context and constraints

*Fable brainstorm session, 2026-07-15. Part of `.notes/sequencer-brainstorm-2026-07-15/`.
This is brainstorm material feeding the Bob-gated `scene-sequencing` co-design —
nothing here is ratified, and no syntax here is a proposal to adopt verbatim.*

## What Belief System taught us (Bob's account, 2026-07-15)

The Ableton + Max for Live rig sequenced a fleet of Pi Zeros via MIDI:

- **What hurt:** encoding sample selection and playback info into note/velocity
  was clunky; automation curves for continuous parameters flooded the network;
  the Ableton set became unwieldy; scatter/group devices were bespoke M4L hacks.
- **What worked:** *track = behaviour* as an organisational principle (one track
  scatters a sound family, another drives points, mix and match); **follow
  actions** produced a generative, self-running programme; the session-view
  grid as the performance surface.
- Also in the mix: a particle system driving points through the space, and an
  auxiliary multichannel system triggered alongside the fleet.

## Bob's two sequencing intuitions

1. **Clip launcher with scripts in the clips.** Ableton session-view grid;
   each clip holds a small script describing a behaviour; clips compose across
   time via launching, loops, and follow actions. Bob's 2026-07-08 design notes
   (in `scene-language-spec.waiting/`) already sketch this: tracks as
   organisational lanes, master scene column, codebox inspector,
   oneshot/loop + follow actions, musical *and* clock time, OSC address
   ergonomics, high throughput awareness.
2. **Video textures as spatial modulation.** Overlay video on the seat map,
   sample each seat's (x,y) in the texture, extract parameters from
   channels/layers. Very visual, very low-friction authoring; finicky mapping
   is the known risk. The `video-mask.waiting` stitch already holds this idea
   and notes the bandwidth question and the "bake to automation" option.

## What the platform already gives us (contract v1.5 facts)

- **Ratified Sequencer tab.** The six-tab IA (Dashboard / Seats / Devices /
  Patches / Assets / Sequencer) already reserves the home. The dashboard
  backend is the clock leader and the natural sequencer host (thread
  instructions agree; standalone app is the named fallback).
- **Cues with fleet-accurate timing.** `/cue <id> <sharedTimeNs>` broadcast;
  each node converts to local monotonic time and fires the bare `/cue <id>`
  to its engine. Cues are *declared in the patch manifest* (id, label,
  description) — the sequencer can render a palette of what the loaded patch
  responds to. Bob: "we can probably drive a whole show just using cues."
- **Params declared in the manifest** (typed, ranged, grouped, nested paths
  incoming via `parameter-addresses`) — the sequencer can render/validate
  targets instead of guessing addresses.
- **Selectors:** `/<id>/`, `/all/`, and lowercase groups `/g1/` (ratified
  2026-07-15, in flight). Tracks can bind to a selector.
- **`/pt` points:** broadcast one frame, node-side proximity decomposition per
  element, shaped scalars, silence = hold, catch-up on (re)appearance. The
  proven pattern for "one compact message, N devices each compute their own
  value."
- **bop ramp pairs:** bop notates breakpoint automation as `param v1 t1 v2 t2 …`
  (value/duration pairs). A destination+duration pair sent once decomposes
  node-side into a smooth ramp — long continuous modulation without streaming.
- **Positions live in the framework.** bopos.py already evaluates fields
  (point proximity) at element positions — nodes can evaluate *other* analytic
  functions of (x,y) if the contract grows a term for it.
- **Sim fleet + audition rig:** `tools/simfleet.py` (protocol) and audible
  audition instances (sound) are config-compatible — a sequencer can be
  developed and *heard* with zero hardware.

## Hard constraints to respect

- **Transport law:** broadcast only for low-rate idempotent one-to-many;
  every fleet command full-state + idempotent; **never per-device streams**
  (the O(N) `/p/gain` streaming model was built and reverted 2026-07-10 —
  this is the exact failure mode Belief System's automation curves had).
- **PD floats are 32-bit** — no absolute time, no >6-sig-fig values through PD.
  All timing math stays in bopos.py; engines get relative fires only.
- **Seam law:** the framework transports values, never composes them into
  patch parameters. A sequencer *sends* values; nodes/patches *shape* them.
- **Decision gates:** scene-language syntax is a co-design with Bob, never
  solo. The whole `scene-sequencing` thread is paused pending Bob's unpause.
  This folder is input for that session, not implementation.
- **Agent-coded composition is first-class** (thread goal): scenes must be
  plain text, forgiving, documented by example, git-friendly.

## The one-sentence synthesis

Everything hard about Belief System's sequencing came from forcing behaviours
through a *dumb* wire (MIDI notes, streamed automation); everything bopOS has
built since is a *smart* wire (declared cues/params, shared clock, node-side
decomposition) — so the sequencer's job is not to stream control, it is to
**compile behaviours into compact terms the fleet already knows how to expand**.
