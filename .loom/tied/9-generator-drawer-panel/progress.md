# Progress — 9-generator-drawer-panel

2026-07-27. The generator drawer's interior now speaks the ratified panel
language. The shell (subpanel, indent, kind tabs) already did; the body was
still the Show inspector's.

## What landed

`param-generator.js`
- `previewGeometry(parsed, declaration, repeats)` — the sampling extracted from
  `preview()` so the Show figure and the panel display are two framings of one
  geometry rather than two copies of the maths.
- `waveTrace()` / `waveDisplay()` — the display the drawer is built around:
  cyan trace, the shape select **inside** it bottom-right, an anchored playhead.
- `panelFields(declaration, parsed, motion)` and `panelSegmentRow()` — the
  panel body. Same `data-param-*` hooks as `fields()`, so `compile()`, the
  drawer binding and the wire could not tell which renderer drew the drawer.
- `compile()` gained one additive clause: a `[data-param-from-enabled]` gate,
  honoured when present.

`control-surface.js`
- `drawerMotion()` — the playhead's honesty rule.
- The drawer renders `panelFields`; `.live-param-gen-preview` is gone (the
  display IS the preview), and an edit redraws the trace only.
- Mini-slider fill/readout sync, the shape→curve rule, the `from` gate.

`control-panel.css` §17 / §17b — the drawer interior, and the metrics the
hosts' touch sizing would otherwise win.

## Decisions taken here

1. **`fields()` was not touched.** It is shared with the Show inspector, whose
   density work is tied and out of this thread. A second renderer beside it,
   with identical hooks, is the smaller change than regrinding a surface this
   thread has no mandate over.

2. **One period, not two** (Bob, live). The Show inspector draws two cycles —
   it is reading matter and the repetition says "periodic". The panel display
   is an instrument face: one period, legible at a glance, and the playhead
   then means exactly one period. `repeats` defaults to 2 so the Show
   inspector is unchanged.

3. **Curve only where curve bites** (Bob: "if curve has no effect on lfo it
   should be removed"). Checked against the engine, `python/paramgen.py`
   `_lfo_value`: `tri` and `saw` run their ramp through `_shape`, and `drift`
   shapes its interpolation between random targets; `sine`, `square` and `sh`
   ignore the option. So the control appears for those three shapes only, and
   changing to a shape that ignores it **zeroes the value** as well as hiding
   it — otherwise a stale bend rides out on the next Apply.

4. **The fade's `from` is stated by an unlabelled latching box** (Bob). Absent
   `from` is a real, meaningful state — "start from wherever the parameter
   is" — and an empty field could not say it out loud. Off: the field is
   inert and no `from` reaches the wire. The Show inspector has no such box,
   and there an empty field still means absent (`compile()` honours the gate
   only when it exists).

5. **The playhead is never invented.** It moves only when a periodic generator
   is running AND the drawer is showing it rather than an edited draft — the
   `8-kind-feedback-pass` ruling generalized. Editing removes it; it is
   anchored by negative delay, the marker's mechanism, so the heartbeat
   re-render cannot restart it.

6. **The drawer is a fixed instrument face, right-aligned** (Bob, live). Apply
   and Stop moved out of the head row into the column beside the display, which
   let the drawer stop stretching to the panel's width: capped at 460px, the
   kind tabs land at about a third each — the Excalidraw's proportions. It is
   aligned to the panel's RIGHT edge, not indented from the left, because the
   pointer sits at `right:9px` — the centre of the row's 18px ∿ column — and a
   left-aligned drawer would point at nothing. `justify-self:end` with an
   explicit width, not an auto margin: an auto margin cancels a grid item's
   stretch, which resizes the drawer to its content and squeezes the display.

7. **Curve's slider range is ±4** (2^±4, a 16× bend). The grammar's exponent is
   unbounded and a slider has to choose. **Worth Bob's eye** — it is the one
   place the panel is less capable than the Show inspector's number field.

## Verification

`tests/verify_generator_drawer.py`, the living journey that owns this surface,
extended: the drawer is built around a display with the shape picker inside it,
shaping args are mini-sliders, min/max/period sit in one args row, the Show
inspector's markup is gone from this host, curve appears for tri and not for
sine or square, and — at the wire — a fade applied with the box off carries no
`from` while checking it puts the typed start value on the wire. All PASS.

`tools/run-tests.sh all`: see the tie commit.
Screenshots: LFO (sine + tri), fade, loop, dark and light, at 1440px.
