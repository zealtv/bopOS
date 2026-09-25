# Roadmap — feasibility, low-hanging fruit, first slices

*Fable brainstorm, 2026-07-15. Ordered so every rung is a usable instrument on
its own, each verified against simfleet + the audition rig (hearable, zero
hardware). Contract-touching rungs are flagged — those need Bob's ratification
per house rules.*

## Rung 0 — Cue board *(no contract change; buildable today)*

A Sequencer-tab panel: the manifest-declared cues of the active patch as
buttons, each with a target selector (all / group / seat), fired through the
existing `/cue` + clock-sync plane. Add a "burst" option (fire cue at k random
seats — dashboard-side randomness, unicast). **This alone upgrades "we can
probably drive a whole show with cues" from theory to practice**, and it
forces the first pass over the plumbing every later rung reuses (sequencer →
relay internal API).

## Rung 1 — Cue clips + the grid chrome *(no contract change)*

The launcher skeleton: tracks, clips, scene column, launch quantization,
oneshot/loop, follow actions. One clip type: the **cue clip** (timed cue list
with waits and simple loops). Transport with optional tempo. Shows as
files (`show.json` + clip files). This is the moment the generative
follow-action magic from Belief System comes back — with maybe 20% of the
eventual system built.

**Rung 1 is the recommended first slice.** It is small enough to spec tightly,
it delivers the emotionally significant capability (a self-running programme),
and nothing in it prejudges the language co-design — cue lists are so simple
their notation barely counts as syntax, and the grid chrome is language-
agnostic. It also produces the perfect concrete artifact to *start* the
language co-design session from: a working grid whose clips are begging to
say more.

## Rung 2 — Ramp clips *(likely small contract/patch-convention work)*

Breakpoint automation compiled to node-decomposed ramps. Decision needed on
*where ramps decompose*: bopos.py ramping `/p` values toward the engine
(framework-side, works for every engine, but flirts with the seam law) vs a
patch-side convention (bop-style `v t` pairs into a declared param — seam-pure,
needs starter-kit abstractions). That's a design-session question with real
trade-offs; the answer probably wants to be the patch-side convention with a
starter-kit `[bopos.ramp]` helper, since the seam law has won every previous
argument.

## Rung 3 — Point clips *(no contract change)*

Animate `/pt` within its existing budget: authored paths, orbits, bounce,
a simple particle emitter (Belief System's particle system as a clip type).
The Seats map renders them live already — authoring UI is drawing on the map.

## Rung 4 — `/field` term + field clips *(contract revision — the big ask)*

The §03 analytic-field primitive: gradients/noise evaluated node-side with
node-side time evolution, `/pt`'s sibling in every design property. One
broadcast per gesture at any fleet size. Field clips + map overlay preview.
This is the highest capability-per-message idea in the whole brainstorm and
the natural headline of the contract proposal that comes out of the design
session.

## Rung 5 — Video clips as baker *(no new wire surface)*

Offline sampler: video file → per-seat channel curves → simplified ramp
segments → played as ramp clips. Bob's visual authoring workflow, zero
runtime cost beyond ramps. (Live texture sampling stays gated and
rate-limited — §03B.)

## Rung 6+ — later, explicitly

Script clips with the co-designed language; pattern clips (intermals-descended
rhythm); scatter as a node-side seeded primitive (worth ratifying alongside
`/field` if the design session likes it); scene crossfade semantics; MIDI
grid-controller launch; field-fitting live video; external-destination tracks
(auxiliary sound systems).

## Feasibility notes

- **Backend fit:** the dashboard backend already runs the leader clock and
  async loops for sync/points; a transport + lookahead interpreter is the
  same kind of citizen. Headless tests: drive the sequencer against simfleet,
  assert on received OSC timing (the existing verify pattern extends
  naturally — this is very testable work).
- **Risk to watch:** the sequencer becomes a second place that "owns" fleet
  state (a field clip and a manual Seats-tab tweak fight over the same
  param). Mitigation is the v1 semantics: full-state idempotent writes,
  last-writer-wins, and the dashboard showing *who last wrote* a value if it
  gets confusing. Don't build arbitration; build visibility.
- **Sequencing vs the queue:** none of this pre-empts the current ui-tabs
  next-sweep order. Rung 0/1 slot naturally after the parameter/group
  foundation lands (groups make track targeting properly expressive), and
  the design session for language/`/field` can happen whenever Bob wants to
  unpause `scene-sequencing`.
