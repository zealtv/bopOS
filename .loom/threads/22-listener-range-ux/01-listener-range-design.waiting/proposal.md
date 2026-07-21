# Listener range interaction — UX proposal

**Stitch:** `22-listener-range-ux/01-listener-range-design`
**Date:** 2026-07-21
**Status:** awaiting Bob's ratification. Nothing implemented; `spatial.js` and
`style.css` untouched.

---

## 1. What is actually there today

`dashboard/static/js/spatial.js`, render (lines ~134–145):

```js
const hx = Math.sin(heading) * range, hy = -Math.cos(heading) * range;
el("line",   {x1:0, y1:0, x2:hx, y2:hy, class:"listener-heading"}, g);
el("circle", {cx:hx, cy:hy, r:0.12,     class:"listener-tip"},     g);
el("circle", {r:0.3,                    class:"listener-body"},    g);
```

The heading line's **length is the range**. The tip sits `range` metres from the
body, and `headingDrag` (lines ~213–233) writes both fields from one pointer
position:

```js
listener.heading = round((Math.atan2(dx, -dy) * 180 / Math.PI + 360) % 360);
listener.range   = round(Math.min(Math.max(distance, LISTENER_RANGE_MIN), diagonal));
```

Three consequences, all of them the defect Bob hit:

1. **The control leaves the map.** With the listener at `(3, 0.4)` in a 6×8 m
   room, the diagonal ceiling is 10 m. Every range above ~0.4 m *in the northerly
   heading* needs a pointer position outside the SVG. You physically cannot
   express it.
2. **Range and heading are one gesture.** You cannot change heading without
   disturbing range, or vice versa. Every re-aim is a re-dial.
3. **The indication is the control.** The "knobbly line" is doing double duty as
   a direction pointer and a magnitude readout, and reads as neither clearly.

Two more facts that bound the solution space:

- `dashboard/state.py:733` — the **server** also clamps:
  `range_m = min(max(range_m, LISTENER_RANGE_MIN), diagonal)`. Raising the
  ceiling is a two-file change, not a CSS one.
- The puck renders only under `installation.simulation?.active`
  (`spatial.js:135`), and there is currently **no numeric listener UI anywhere** —
  no field in the Seats sidebar, nothing in `index.html`. Range has exactly one
  input path, and it's the broken one.

---

## 2. Design principles taken from the brief

- **P1** — the range gesture starts and stays on/at the listener dot. Nothing
  travels away from it.
- **P2** — heading and range are visibly and physically separate controls.
- **P3** — range is *shown* as a field (gradient + thin outline), not as a line.
- **P4** — every value reachable by mouse is reachable by touch and by keyboard
  or a typed number.
- **P5** — the wire is unchanged; live 40 ms throttled `set_listener` during the
  gesture stays.

---

## 3. Alternatives

Four sketched. A, B, C are genuine competitors; D is the passive-only baseline
the brief named, kept because part of it survives into the recommendation.

### A. Radial scrub collar (drag out/in from a ring hugging the dot)

A thin ring is drawn just outside the listener body at a **fixed** radius
(~0.45 m map units — it never grows with range). Press it and drag; only the
*change* in your distance from the listener body is read, at a gain, so the
pointer never needs to be `range` metres away.

```
        ╭──────────╮  ← scrub collar, fixed radius, always on the dot
        │   ╭──╮   │
        │   │L │───────→  heading handle (fixed short length)
        │   ╰──╯   │
        ╰──────────╯
            ↑ press here and drag outward → range grows
              (1 m of pointer travel = 2.5 m of range)

  range field, drawn passively, clipped to the room:
   ░░░░░░░░░░░░░░░░
  ░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░
  ░▓▓▓▓▓▓█▓▓▓▓▓▓▓▓▓░      █ = listener
  ░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░      ▓░ = radial gradient falloff
   ░░░░░░░░░░░░░░░░       ─── thin outline at the range radius
```

Relative, not absolute: `range += (distanceNow − distanceAtLastMove) × gain`,
clamped. Shift-drag = 0.25× gain for fine work.

- **Map edges:** solved completely. The gesture is bounded by the collar, and
  even a listener in the corner has 360° of collar to push off. Worst case the
  pointer runs out of *window*, and a 2.5× gain means 4 m of screen travel
  covers a 10 m diagonal.
- **Extreme ranges:** the pointer never tracks the ring, so a 40 m range is the
  same gesture as a 4 m one — just longer, or one shift-free flick plus a second.
  Ceiling is a policy choice, not a geometry limit.
- **Touch:** good. A radial drag is the most touch-native gesture there is, and
  the collar can carry a transparent ~14 px non-scaling hit stroke to reach a
  44 px target without visually thickening. It does collide with map panning if
  we ever add pan — worth noting, we don't have it.
- **Risk:** relative scrubbing is invisible until you try it. Needs the collar
  to look like a grab-me thing (hover lift + `cursor: ns-resize`/`ew-resize`) and
  a live numeric readout so you learn the gain in one drag.

### B. Rotary dial on the dot (knob rotation → range)

Press the collar and *rotate* around the listener. Accumulated angle maps to
range: a 270° sweep spans min→max, and rotation accumulates past a full turn so
extreme ranges stay reachable.

```
        ╭───↷──────╮
        │   ╭──╮   │      rotate clockwise → range up
        │   │L │───────→  heading handle unchanged
        │   ╰──╯   │
        ╰──────↶───╯
```

- **Map edges:** solved — the gesture is entirely local.
- **Extreme ranges:** solved by accumulation; but the mapping (degrees→metres) is
  arbitrary and unlearnable without a readout.
- **Touch:** **poor.** Rotating around a ~30 px target with a finger that
  occludes it is the classic bad mobile knob. Precision collapses; angle
  wraparound near the centre produces jumps.
- **Killer objection:** the map already spends rotation semantics on heading.
  Two rotational gestures on the same 60 px of pixels, meaning different things,
  is exactly the confusion P2 exists to prevent.

### C. Grab-the-ring-anywhere (drag the range circle itself)

The range outline becomes the control: press anywhere on its circumference and
drag radially.

```
      ╭───────────────╮   ← this whole ring is draggable
      │               │
      │       █       │
      │               │
      ╰───────────────╯
```

- **Map edges:** **improved but not solved.** A listener at the top edge with a
  10 m range still has most of its circumference off-canvas — you can grab
  whatever arc remains visible, but if the range is large enough that *no* arc is
  on-canvas (listener in a corner, range > diagonal-ish), the control disappears
  entirely. That is the same class of bug, just rarer.
- **Extreme ranges:** the failure above is precisely at extreme ranges — the
  regime Bob cares about.
- **Touch:** fine where the ring is visible.
- **Verdict:** violates P1 (the control travels with the value) and only
  partially fixes the reported bug. Reject.

### D. Inspector numeric field + passive range ring (no map gesture)

Add a **Listener** bar to the Seats toolbar area, modelled on the existing
`#point-editor` row in `index.html` (same pattern, same styling, appears only
when `simulation.active`):

```
  ┌──────────────────────────────────────────────────────┐
  │ Listener   x [ 3.0 ] y [ 0.4 ] m   heading [ 90 ]°   │
  │            range [ 7.5 ] m  ├────────●─────────┤     │
  └──────────────────────────────────────────────────────┘
```

The map ring becomes read-only.

- **Map edges / extreme ranges / touch:** all trivially fine — it's a number
  box. Nothing can clip.
- **Cost:** loses direct manipulation entirely. Setting range while listening is
  a spatial, ear-driven act ("push it out until seat 4 drops away"); a number box
  makes that a guess-and-check loop. A regression in feel even though it is a fix
  in function.
- **But:** as a *second* path alongside a gesture, it is the keyboard/numeric
  answer P4 demands, and it is cheap. It survives into the recommendation.

---

## 4. Recommendation

**A + D: a fixed radial scrub collar on the dot, a shortened fixed-length
heading handle, and a Listener bar with a typed range field.** Range is
indicated by a clipped radial-gradient field with a thin outline. Reject B
(touch-hostile, rotationally ambiguous with heading) and C (does not actually
fix the edge case).

Reasoning:

1. It is the only option that makes range **unconditionally settable** regardless
   of where the listener sits or how large the range is — the actual bug.
2. It obeys P1 literally: nothing about the control moves off the dot, ever.
3. It separates the two controls physically (collar = magnitude, tip = direction)
   and, critically, *by gesture kind*: radial push/pull vs. aim. B and C both
   leave them sharing a gesture family.
4. Touch is the strongest of the four.
5. The numeric field costs one row of HTML and buys keyboard access, precise
   values, and a place for the live readout that teaches the scrub gain.

### Anatomy

```
                    (range field, clipped to the room rect)
      ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
     ░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░
     ░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░
     ░▓▓▓▓▓▓▓▓▓▓▓╭────────╮▓▓▓▓▓▓▓▓▓▓▓▓░
     ░▓▓▓▓▓▓▓▓▓▓▓│  ╭──╮  │▓▓▓▓▓▓▓▓▓▓▓▓░   ── thin outline at r = range
     ░▓▓▓▓▓▓▓▓▓▓▓│  │L │──┼──────→        ── heading handle, FIXED 0.9 m
     ░▓▓▓▓▓▓▓▓▓▓▓│  ╰──╯  │▓▓▓▓▓▓▓▓▓▓▓▓░
     ░▓▓▓▓▓▓▓▓▓▓▓╰────────╯▓▓▓▓▓▓▓▓▓▓▓▓░
     ░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░       ↑ scrub collar, FIXED 0.45 m
      ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

Three hit regions, all on the dot, all disjoint:

| region | radius | gesture | writes |
|---|---|---|---|
| body | 0 – 0.30 m | drag | `x`, `y` (unchanged behaviour) |
| collar | 0.30 – 0.55 m | radial drag | `range` |
| tip | at 0.9 m, r 0.12 | drag | `heading` **only** |

The tip becomes a *pure* heading handle: it always sits 0.9 m out, never
encodes magnitude, and `headingDrag` drops its `range` write. That alone
resolves defect (2).

### Interaction detail

- **Scrub gain:** `range += Δdistance × 2.5`, clamped. Shift = ×0.25.
  Double-click the collar resets to `default_range()` (3 m).
- **Wheel:** wheel over the puck = ±0.25 m/notch (±0.05 with shift). Free, and
  the fastest path on a trackpad.
- **Keyboard:** the puck gets `tabindex="0"`. `↑`/`↓` = ±0.1 m range,
  `Shift+↑/↓` = ±1 m; `←`/`→` = ∓1° heading, shift = ∓15°. (`svg.onkeydown`
  already exists for seat Enter/Space — extend it.)
- **Numeric:** `#listener-range` in the Listener bar, `type=number`,
  `min=0.5 step=0.1`, committing on change. Same bar carries a live readout that
  updates during the scrub, so the gain is legible.
- **Live feedback:** unchanged — mutate the SVG directly, `set_listener` throttled
  at 40 ms, final send on `pointerup`. Same code shape as today.
- **Touch:** the collar carries a transparent hit stroke
  (`stroke: transparent; stroke-width: 16; vector-effect: non-scaling-stroke`)
  giving a ≥44 px target without visual weight; the tip gets the same treatment.

---

## 5. Visual treatment (both themes)

Range is drawn as a **radial gradient disc + thin outline**, clipped to the room
(`#spatial-room-clip` already exists — `spatial.js:147` uses it for point
handles). The knobbly line is retired as a magnitude cue.

Colour comes from **existing tokens only**, so `21-theme-cyan-tint` retunes this
for free. Two new *semantic* aliases so the field is retunable independently
later:

```css
:root { --listener-field: var(--sim); --listener-ring: var(--sim); }
```

| element | dark (`--sim` #6FB3E6) | light (`--sim` #2464A8) |
|---|---|---|
| field, centre stop | `--listener-field` @ 0.20 alpha | @ 0.14 alpha |
| field, edge stop | same hue @ 0.00 | same @ 0.00 |
| range outline | `--listener-ring` @ 0.75, 1.5 px non-scaling | @ 0.85, 1.5 px |
| collar (rest) | `--listener-ring` @ 0.35, 1 px | @ 0.45, 1 px |
| collar (hover/drag) | `--accent-cyan` #8FE3DE, 2 px | `--accent-cyan` #147772, 2 px |
| heading handle + tip | `--accent-cyan` | `--accent-cyan` |
| body / label | unchanged (`#f5f7fa` on `#0b0e11`) | unchanged |

Rationale: `--sim` is *already* the simulation-context hue in both themes, and
the listener exists only in simulation — the field should read as "this is the
simulated ear", not as a seventh element colour. `--accent-cyan` for the active
collar and the heading handle keeps the two *controls* in one family, distinct
from the *field*, and lands squarely in the purple-and-cyan direction thread 21
is heading. Nothing here uses `--green`, so a `--green` retune or removal in 21
cannot regress it.

Light-theme contrast: the outline at `#2464A8` @ 0.85 over `--canvas` #ece8f1 is
≈ 4.9:1 — above the 3:1 non-text minimum with headroom. Dark: #6FB3E6 @ 0.75 over
#12171c ≈ 7.4:1.

The gradient uses a single `<radialGradient>` in the existing `<defs>`; falloff
stops at `[0 → 0.20a, 0.55 → 0.11a, 1 → 0a]` so the field reads as *falloff*, not
as a flat disc, without implying a specific audition curve.

---

## 6. Answers to the system constraints

**Simulation-only rendering.** Unchanged: the whole puck, collar, field and
Listener bar are gated on `installation.simulation?.active`. The Listener bar
follows the `#point-editor` precedent — present in the DOM, `hidden` when
inactive. No range UI exists outside simulation, which is correct: range means
nothing to the live fleet.

**The `[LISTENER_RANGE_MIN, diagonal]` clamp — keep the ceiling.** Recommend
**yes, keep it**, unchanged, in both `spatial.js` and `state.py:733`. The room
diagonal is the largest distance between any two points in the room; a range at
the diagonal already reaches every seat from every listener position, so ranges
beyond it are audibly identical and semantically meaningless. Keeping it also
means **zero server change** — this stays a pure UI stitch, as the brief wants.
The clamp was never the bug; the *only* reason it felt like one is that the
handle geometry made the top of the range unreachable, and A removes that.

**How an over-map range reads.** Even under the diagonal ceiling, an off-centre
listener's ring routinely leaves the room rect. Treatment:

```
   room edge ┐
  ┌──────────┴───────────────────────────┐
  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░                 │   field clipped at the wall
  │▓▓▓▓▓▓█▓▓▓▓▓▓▓▓▓▓▓░░░                 │
  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░                  │
  ╞══════════════════╡ ← outline continues as a DASHED arc where
  │                       it falls outside the room                   │
  └───────────────────────────────────────┘
```

- The gradient field is clipped to the room (`clip-path`), so it never bleeds
  over the tray or the sidebar.
- The **outline is not clipped** — it renders as a solid arc inside the room and
  a 4-2 dashed arc outside it, at 0.5 alpha. You always see the true circle;
  "outside the room" is legible as dash rather than as absence.
- When the range reaches the ceiling, the outline switches to a 2 px solid stroke
  and the Listener bar readout says `7.5 m (max)`. That is Bob's "outline showing
  the maximum range", earned rather than drawn as a separate ring.
- If the ring is *entirely* outside the room, the field simply fills the room —
  the correct reading ("everything is in range") — and the bar carries the number.

**Touch and keyboard/numeric.** Both first-class, specified in §4: 44 px
transparent hit strokes for collar and tip, radial drag as the touch gesture
(no rotation, no long-press), plus `tabindex` + arrow keys on the puck and a
typed `range` field in the Listener bar. Every value is reachable three ways.

**Wire unchanged.** `set_listener` still carries `x`, `y`, `heading`, `range`.
No contract amendment. `clean_listener` untouched.

**Live feedback preserved.** The scrub mutates the SVG in the move handler and
sends throttled at 40 ms exactly as `headingDrag`/`listenerDrag` do now, with a
final unthrottled send on `pointerup`. The Listener bar's readout is driven from
the same handler, so the number and the ring move together.

---

## 7. Open questions for Bob

1. **Scrub gain 2.5×** — is push-to-grow at 2.5 m of range per 1 m of pointer
   travel the right feel, or should it be pointer-absolute-from-collar (1×) with
   the understanding that you may need two drags for a big room?
2. **Keep the diagonal ceiling?** I recommend keeping it (§6) and touching no
   server code. Say if you want range unbounded above — that reopens
   `state.py:733` and makes this a two-plane change.
3. **Heading handle length 0.9 m** — fixed in *map metres* (scales with zoom, is
   proportional to the room) or fixed in *screen pixels* (constant on-screen size
   in any room)? Metres is simpler and matches every other puck dimension;
   pixels is more usable in a very large room.
4. **Where does the Listener bar live?** Proposed: in `#point-toolbar`'s strip
   above the map, matching `#point-editor`. Alternative is the Seat sidebar under
   Venue. The toolbar keeps it beside the thing it controls; the sidebar keeps
   the map chrome thin.
5. **Does the field replace the knobbly line entirely,** or do you want a faint
   radial tick from the body to the ring as a residual magnitude cue? I propose
   full replacement — that is what §3 P3 asks for — but it is a taste call.

---

## 8. If ratified

`02-listener-range-implementation` builds it: `spatial.js` (render + three hit
regions + scrub/wheel/key handlers), `style.css` (tokens, gradient, dashes),
`index.html` (Listener bar), `dashboard.js` (bar binding), and a Playwright
guard proving range is settable with the listener at each of the four corners at
the maximum clamp — the exact case that is impossible today.
