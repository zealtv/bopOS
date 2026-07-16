# Spatial fields and the video-texture idea

*Fable brainstorm, 2026-07-15. Companion to §02 — this is the "field clip" and
"video clip" story, and the resolution of the `video-mask` question.*

## One pipeline, three producers

Everything here is the same shape — the shape `/pt` already ratified:

```
mask(x, y, t)  →  per-seat scalar  →  parameter on that seat's patch
```

The producers differ in *where the mask is evaluated* and therefore what it
costs on the wire:

| producer | evaluated | wire cost | expressive range |
|---|---|---|---|
| **A. Analytic field** | node-side | ~1 broadcast per gesture | parametric: gradients, waves, noise, orbits |
| **B. Live texture sampling** | dashboard-side | bounded stream (mitigations below) | anything you can draw/render/play |
| **C. Baked texture** | offline → ramp playback | ramps only | anything, authored in advance |

The strategic claim: **A covers most of the artistic wishlist at almost zero
network cost, C makes video an authoring format rather than a runtime, and B
is the special case to rate-limit, not the default.** This matches Bob's
2026-07-08 instinct ("if gradients can be created then that mostly dissolves
the video-mask approach") — but the video *workflow* survives in C, which is
the part Bob actually loves (visual, low-friction authoring).

## A. Analytic fields — the `/field` term (contract revision required)

Generalise `/pt`'s trick. Nodes already know their element positions (bopos.py
evaluates point proximity per element). A field is a broadcast primitive with
**node-side time evolution**, so animation is free:

```
/field <fieldId> <shape> <shape-params…> <animation-params…> → /p/<name>-ish binding
```

Illustrative shapes (each maps a seat's (x,y) → 0..1):

- **linear** — angle, wavelength, phase, *phase-velocity* → a gradient that
  sweeps across the room forever on one message.
- **radial** — centre (x,y), radius, falloff enum (reuse `/pt`'s 0/1/2),
  *radius-velocity* → breathing circles; with angular section params, a
  rotating radar wipe.
- **spin** — centre, angular offset, *angular velocity* → the spinning
  gradient from Bob's list, one message, spins until told otherwise.
- **noise** — seeded value-noise with spatial scale and *scroll/evolve
  velocity* → shimmering textures; seeded, so every node computes the *same*
  field deterministically.
- **const** — the degenerate but useful "hold everyone at v".

Design properties (all inherited from `/pt` precedent, which is why this is a
plausibly small contract amendment rather than a new plane):

- **Full-state & idempotent**: every `/field` message carries the complete
  field definition including its epoch-phase, so re-broadcast is always safe
  and loss self-heals on the next assert. Slow re-assert (~1 Hz) keeps
  latecomers/lossy nodes converged — like `/pt`'s catch-up.
- **Silence = hold**: a field keeps evolving node-side until replaced or
  cleared (`/field/clear <id>`).
- **Time base**: evolution phase must reference the shared clock (the
  clock-sync offset already on every node) so all seats agree where the
  gradient *is*. Phase-as-ns-string, per the §12 float law.
- **The binding question** (for the design session): does a field target a
  parameter name directly (framework writes `/p/<name>` — flirts with the
  seam law), or is it delivered like points as `/field <id> <element> <v>`
  and the *patch* maps it (clean seam, matches `/pt` exactly)? The `/pt`
  precedent says the latter: shaped scalars in, patch decides meaning.
- **Composition**: multiple simultaneous fields with distinct ids, like
  points. v1: they don't blend in the framework; a patch consuming two field
  scalars combines them however it likes (seam law again).

**Why this is the crown jewel:** a 100-seat fleet gets a room-wide animated
gradient for the cost of one broadcast per *gesture change*, not per frame.
This is the exact opposite of the Belief System automation flood, and no
other architecture on the table can touch it.

## B. Live texture sampling — allowed, but domesticated

For genuinely unpredictable sources (live video, a particle sim you're
steering, a webcam): dashboard samples the texture at seat positions. The raw
form (per-seat values at 30 Hz) is the banned O(N) stream. Two mitigations:

1. **Piecewise-linearisation**: instead of streaming values, the sampler
   emits short *predictive ramps* per seat at 2–5 Hz ("head to 0.62 over
   250 ms"). Node-side ramping smooths between updates; a lost packet means a
   briefly stale trajectory, not a stuck value. 100 seats × 3 Hz ≈ 300 small
   unicasts/s — still heavy; fine at 30 seats. Honest verdict: works for the
   current scale, caps fleet size, so it must never be the default path.
2. **Field-fitting (the clever option)**: fit the *texture* to the analytic
   basis — approximate the current frame as e.g. linear + radial + noise
   residual and broadcast the fitted field params instead. Lossy but
   room-scale-plausible (these are speakers metres apart, not pixels). This
   turns arbitrary video into A-cost traffic. Research-flavoured; park it as
   a delicious later experiment.

## C. Baked video — video as an *authoring format*

The workflow Bob finds appealing, kept whole; only the runtime changes:

1. Author in anything (After Effects, TouchDesigner, Processing, a phone
   video of ink in water).
2. The Sequencer's video-clip importer samples the file offline at each
   seat's (x,y) per frame, per selected channel (lum / R / G / B / layer).
3. Output: per-seat breakpoint curves, **simplified** (Ramer–Douglas–Peucker
   or similar) into few-segment ramps.
4. The clip plays those back through the ramp compiler like any ramp clip —
   pre-scheduled, node-decomposed, near-zero live bandwidth, loss-tolerant.

Channel→parameter mapping (the "finicky" worry) gets one honest UI: the video
clip inspector lists channels; each channel gets a target (param/point-like
binding) and a range. Lighting-world pixel mapping does exactly this and it's
fine *when the preview is good* — which leads to:

## The map is the monitor

The Seats tab map is already the spatial visualiser. Field and video clips
should render their mask *on the map* (a translucent overlay animating over
the seat dots) both when auditioning and live. This is most of the video
idea's UX appeal — you see the sweep move across the room — and we get it for
analytic fields too, since the dashboard can evaluate the same primitive for
display. One renderer serves: authoring preview, live monitoring, and the
audition rig (hear it *and* watch it, no hardware).

## Verdict for the design session

- Propose `/field` as an additive contract term (the `/pt` sibling). It
  dissolves `video-mask`'s runtime as predicted, at spectacularly better
  bandwidth than anything else considered.
- Keep video as clip type C — an importer/baker, no new wire surface at all.
- Gate B (live sampling) behind "you asked for it" UI, with the fleet-size
  caveat stated in the inspector.
