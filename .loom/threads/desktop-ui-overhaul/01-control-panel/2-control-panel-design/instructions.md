# 2-control-panel-design

Design the compact control-panel UI from Bob's 2026-07-27 mockup. Written
proposal + mockups/prototype, **Bob ratifies**, then lay out implementation
children. Source of truth: lore
`2026-07-27-control-panel-ui-and-architecture-braindump` (verbatim braindump
+ panel descriptions).

Core direction (from the mockup — refine, don't re-invent):

- Tight, compact, PD/Ableton/Max-inspired; grayscale base, cyan =
  selection and predominantly **modulation**.
- One parameter per line, short rows: value box + named slider + `~`
  generator icon. Icon click expands/collapses an inline generator drawer
  (LFO/loop/fade tabs, waveform display, args); the param stays under
  generator control until manual interaction takes over (§3.2 semantics).
- Generator state always visible on the control: slider fill follows the
  modulated value; toggles flash live value with cyan border; deterministic
  generators also show the precise current value.
- Mixed aggregate rendering: cross-hatch = mixed values; cyan-tinted
  hatch = generator involved; editing unifies to solid.
- Hierarchical addresses accordion (collapse/expand per address level).
- Provisional preset row at panel top (dropdown + new/save/del) —
  placeholder ahead of `41-preset-primitive`; design the slot, don't build
  preset behavior.
- Non-float kinds to cover in the design: toggles, integers, enums
  (wire as integer; automation TBD), and **events** (float singles/pairs/
  triplets — MIDI note/vel/dur — with sync + send, likely a new
  `<target>/e/*` plane). Events are a **contract question**: spec the UI
  shape here, flag the wire plane as a future OSC-contract amendment —
  do not implement the plane in this thread.

Deliver: design doc + design-language rules (the extrapolable tokens/
patterns `02-app-wide-rollout-design` will consume), before/after mockups
against the current `ControlSurface`, and a proposed implementation split.
Mark `.waiting` for Bob's ratification.
