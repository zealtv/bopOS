# Waveform visualisation — accessibility & operational-calm design

Lens: guard the operator's attention and the hardware budget. I did not just
critique; below is a buildable app-wide treatment chosen from this lens, plus
the constraint I believe kills the elegant-but-wrong alternatives.

Everything here is grounded in the real code I read:
`dashboard/static/css/facilitator.css` (`.live-param` is `flex; min-height:44px;
gap:12px`; label `span` `min-width:100px`; `output` `width:58px` tabular; the
`.mixed` slider is `opacity:.64` + a centre-tick gradient), the cue
CSS-progress precedent (`#declared-cues button.scheduling` animates
`background-size` via a single `@keyframes cue-lead`, with a
`prefers-reduced-motion` block that jumps straight to the end state),
`show.js`/`style.css` `show-step-progress` (a pure-CSS `width` animation,
also killed under reduced-motion), `facilitator.js` `paramControl()` /
`aggregateValue()` / `bindCards().send()` (take-over already strips `.mixed`
and sends a plain value), and `docs/OSC-CONTRACT.md` §3.2 (generator kinds:
constant / fade / segment-loop / LFO `sine tri saw square sh drift` / stop;
ints floor-and-emit-per-crossing; catch-up is a computed constant).

---

## 1. Altitude & framing

**I am designing at the altitude of restraint, deliberately.** The brief invites
an "app-wide waveform visualisation." My load-bearing finding is that the
literal reading of that phrase — a live, per-control waveform picture — is
unaffordable and, worse, a *category error* on a slider. So I raise the altitude:
the app-wide primitive is **"this control is automated, this is its kind, this is
its value now, and it is safe to grab"** — carried by a *static, non-motion*
signal first, with motion as cheap optional sugar layered on top. The rich
picture of a waveform is scoped to exactly one place (the Show builder
inspector, `automation-2`), where the operator is authoring one generator with
room and focus.

Two hard truths drive this:

1. **A slider's axis is value, not time.** A waveform is value-over-*time*. You
   cannot honestly paint a time-domain sine along a track whose length already
   *means* the value range — the thumb position and the waveform's x-axis fight
   over the same pixels. Any "waveform on the slider" is either decorative
   (dishonest) or forces a second axis the operator must decode mid-show.

2. **Motion is the least reliable channel we have.** Offline devices cannot
   animate (they hold a stored constant, per the contract). Reduced-motion users
   must not animate. Daylight on a tablet washes out low-alpha motion. So motion
   *cannot* be where "automated" lives — it must be a static, high-contrast,
   theme-portable mark, with motion added only where it survives.

The result is calmer *and* cheaper, which is the happy case where my two mandates
(attention budget, hardware budget) point the same way.

---

## 2. Design (with mockups)

Three layers, in strict cost/reliability order. Layer 1 is mandatory and
static; each layer up is more motion and more optional.

```
 Layer 1  KIND GLYPH  (static, always)   ── the honest "automated" signal.
          Painted in the label. Screen-reader announced. Survives offline,
          reduced-motion, daylight, light theme. Never moves.

 Layer 2  TRACK STATE (static, paint-once) ── the slider track gets an
          "automated" tint + a shape hint drawn ONCE per generator change,
          not per frame. Cached as a layer. Zero per-frame cost.

 Layer 3  VALUE MARKER (motion, budgeted)   ── the thumb / output number moving
          is the animation. It is the value automation-3 already computes.
          One shared clock, ≤20fps, visible controls only. Compositor transform.
```

The kind glyph vocabulary (monochrome, drawn from Unicode or a 1-path inline
SVG so it inherits `currentColor` and survives both themes):

```
  constant / not automated   (nothing — normal control)
  ∿   sine / tri / drift LFO      loop  ⟳      stop/frozen  ▪ (then reverts to none)
  ⌁   saw / square / s&h LFO      fade  ╱      mixed        ∿̸ (glyph + "mixed")
```

I use two glyphs for LFOs (smooth `∿` vs stepped `⌁`) rather than six, because at
15–18px the operator distinguishing sine-from-tri buys nothing and costs legibility;
the exact shape lives in the Show inspector where it matters.

### Slider — the primary case (facilitator/Dashboard live card, `.live-param`)

Current DOM is `<span>label</span><output>0.62</output><input type=range>`. I add
one glyph slot in the label and a paint-once track backdrop. Nothing steals the
44px hit area.

```
 NOT AUTOMATED (baseline, unchanged)
 ┌───────────────────────────────────────────────────────────┐
 │ gain              0.62   ▁▁▁▁▁●▁▁▁▁▁▁▁▁▁                    │
 └───────────────────────────────────────────────────────────┘

 AUTOMATED — sine LFO
 ┌───────────────────────────────────────────────────────────┐
 │ ∿ gain            0.62   ░░░░░░●░░░░░░░░░░  ← track tinted  │
 │ └glyph=kind      └value  └thumb = live value, moving        │
 │   (static,        (live   the tint is the paint-once        │
 │    announced)      text)  "automated" state, NOT a waveform │
 └───────────────────────────────────────────────────────────┘

 AUTOMATED — timed fade in flight (reuse ratified CSS-progress!)
 ┌───────────────────────────────────────────────────────────┐
 │ ╱ gain    →0.90    0.71   ▓▓▓▓▓▓▓░░░░░░░░░  ← CSS width grow │
 │   the fade target shown once; the fill is one @keyframes    │
 │   width animation (show-step-progress precedent). 0 JS.     │
 └───────────────────────────────────────────────────────────┘
```

Key move: **a fade is transient and reuses the already-ratified pure-CSS
`show-step-progress` / `cue-lead` width-growth mechanism** — a single
`@keyframes`, GPU-composited, already has a `prefers-reduced-motion`
kill-switch. When the fade completes it becomes a constant and the treatment
clears. This is the cheapest possible "waveform," and it's the one operators see
most.

The track tint for LFO/loop is a paint-once background (a 2px inset bar in
`--auto`), **not** a redrawn oscilloscope. The *shape* of the LFO is conveyed by
the glyph, not by drawing the curve on the value-axis track (see §1 truth #1).

### Toggle / checkbox (int 0..1)

A binary control cannot carry a waveform and **must not flicker** (flicker is a
seizure/vestibular hazard and pure noise at a glance). Automation on a 0/1 int is
a square/s&h LFO or a fade across the threshold. Treatment: static glyph + the box
reflects the current floored value. **No motion below ~1 Hz-safe, and under
reduced-motion, none at all.**

```
 ⌁ mute-lfo                                   [✓]   ← glyph = automated; box = now
   no blink. The glyph tells you it's live; the box tells you the state.
```

### Numeric / output-only

Same as slider without the track: glyph + live tabular number. The number moving
*is* the visualisation; `font-variant-numeric:tabular-nums` + fixed `58px` width
(already in the CSS) means it updates without reflowing neighbours.

### Aggregate rows (All / Group) — honesty first

`aggregateValue()` already returns `{value, mixed}`. When members carry
*different generators*, we must not fake one moving value.

```
 ALL SEATS · uniform sine LFO           ∿ gain     0.62  ░░░░●░░░░  (animates)
 ALL SEATS · different per-Seat gens    ∿̸ gain     auto·mixed   ── ── ── (static)
```

A mixed-automation aggregate shows the glyph with a **strike/slash** + the text
`auto·mixed`, the existing dashed/`.mixed` static bar, and **no moving marker** —
because there is no single value to move. This extends the existing `.mixed`
affordance rather than inventing a parallel one.

### Show builder inspector (automation-2 scope) — the ONE real waveform

This is the only surface that draws an actual value-over-time curve, because it is
single-focus authoring with room, and time *is* the natural x-axis there.

```
 ┌─ message: /all/p/gain  lfo sine 0.2 0.8 4s ─────────────┐
 │  ┌──────────────────────────────────────────────┐       │
 │  │      ∿           ∿           ∿                 │ 0.8   │
 │  │   ╱     ╲     ╱     ╲     ╱     ╲              │       │
 │  │ ╱         ╲ ╱         ╲ ╱         ╲            │ 0.2   │
 │  └──────────────────────────────────────────────┘       │
 │   one static SVG path, ≤2 cycles, painted on edit.       │
 │   A single slow playhead line is OPTIONAL and gated ≤1.  │
 └──────────────────────────────────────────────────────────┘
```

Static SVG path, redrawn only when the operator edits the generator. At most
**one** such preview exists on screen at a time (it's an inspector), so it can
afford to be nicer — but even here the default is static; the moving playhead is
opt-in and dies under reduced-motion.

---

## 3. Per-surface treatment table

| Surface | Kind glyph | Track/shape | Live motion | Mixed | Offline |
|---|---|---|---|---|---|
| Facilitator/Dashboard slider (`.live-param` range) | yes, in label | paint-once tint; fade = CSS-progress | thumb+number, shared 20fps, visible-only | `auto·mixed`, static bar, glyph+slash, no motion | static stored constant, dimmed, glyph but no motion |
| Toggle/checkbox (int 0..1) | yes | none | none (no flicker) | indeterminate + glyph | static, glyph, no motion |
| Numeric/output-only | yes | none | number only (tabular, no reflow) | `auto·mixed` static | static value, dimmed |
| Aggregate All/Group row | yes (slashed if mixed gens) | as slider if uniform | only if uniform generator | **required honest static** | static |
| Seat detail / patch-editor slider (`dashboard.js`, 15px density) | yes (smaller) | paint-once tint | thumb+number | n/a (single Seat) | static |
| Show builder inspector | header text | **full static SVG curve** | ≤1 optional playhead | n/a | n/a |

---

## 4. Motion & interaction spec

**One shared clock, not forty timers.** A single `requestAnimationFrame` loop
drives every visible automated control. This is the direct analogue of the house
rule that killed per-DOM countdown re-renders in commit `7162943` — motion is
shared and cheap, never per-widget.

- **Tick rate:** throttle the shared loop to **≤20 fps** (50 ms) via a time-delta
  gate inside rAF. A slow LFO or fade needs no more; 20 fps reads as smooth for
  slider motion and quarters the work vs 60.
- **Per visible control per tick:** compute value (automation-3 owns this) →
  write `output.value` (fixed-width tabular, no reflow) + set one CSS custom
  property for the thumb via `transform: translateX()` (compositor-only, no
  layout). ≈2 cheap writes.
- **Visible only:** an `IntersectionObserver` pauses ticking for scrolled-off
  controls. On a 40-card screen a tablet shows ~8–14 at once — that is the real
  working set, not 40.
- **Static backdrops:** painted once on generator change (SVG data-URI background
  or an inset `<i>` element), promoted to their own compositor layer. **0 ms per
  frame.**

### Frame budget — numbers, cheap tablet, screen of ~40 controls

Target: 60 Hz panel, 16.6 ms/frame; I budget the *automation layer* to **≤4
ms/frame** to leave the app its headroom on a Pi-class / 2018-era tablet.

| Design | Per-frame work | Verdict |
|---|---|---|
| **This design** | ~14 visible × 2 compositor-friendly writes, at 20 fps (every 3rd frame). ~28 writes on tick frames, 0 between. Static shapes 0 ms. | **< 0.5 ms/frame.** Fits with 8× headroom. |
| Per-control live oscilloscope (the tempting one) | 40 canvases × clear+stroke ~100-pt path × 60 fps = **2400 canvas redraws/sec**, ~0.3–1 ms each = **700–2400 ms of work per second**. | **Misses every frame. Jank, heat, battery. Dead.** |

**Degradation guardrail:** if the visible automated count exceeds **24**, drop the
shared loop to **10 fps** and suppress the moving thumb (keep static shape +
value snapped ~2×/s). The glyph never degrades — the "is it automated" answer is
always present.

### Take-over (the dying-under-the-finger feedback)

The contract: touching an automated control sends a plain value and kills the
generator. `bindCards().send()` already strips `.mixed`; I extend it:

1. **On `pointerdown`** (before any value change): freeze the marker at the finger,
   and start a **one-shot 200 ms opacity fade** on the glyph + track tint to
   nothing. This is a single-element CSS transition, not per-frame work.
2. **Remove** the control from the shared rAF set (it's now a constant).
3. **Announce** once, politely (see §ARIA).
4. **On release:** send the plain value (existing behaviour).

Crucially, the motion cessation is *not the only feedback* — the glyph
disappearing is a persistent static change a low-vision operator can verify
afterwards, and the announcement covers no-vision. "The animation died" is the
*sugar*; the state change and the announcement are the *substance*.

### Reduced-motion story (mandatory, house pattern exists)

`facilitator.css` already ships `@media(prefers-reduced-motion:reduce)` for the
cue button (jump to end state) and `style.css` for `show-step-progress`
(`animation:none`). I mirror it exactly:

- **No thumb sweep, no fade-fill animation, no playhead.** The value still
  *updates*, but as discrete text snaps at ≤2 Hz — informative without vestibular
  motion.
- **The kind glyph carries the entire indicator**, which is why it had to be
  static and mandatory. Reduced-motion loses nothing essential.
- Take-over fade → instant removal.

### Contrast, daylight, and the coming light theme

Today is `color-scheme:dark only` and there is **no `prefers-color-scheme`
anywhere in the CSS** — so I must not bake a black-only wash (the
`rgba(...,.14)` alpha look used by `show-step-progress` is invisible in daylight
and inverts wrong on white).

- Introduce **one semantic token, `--auto`**, distinct from `--green` (value/
  online), `--red` (mute/danger), and `--amber` (crashed engine / paused — do
  **not** reuse amber, it already means "crashed"). Proposal: a calm cyan-blue,
  in the family the Show pills already use (`#9fd4f5` on `#122736`).
- Ship it **themed from day one**, keyed off both the media query and the
  anticipated `data-theme` attribute, so contrast holds on white:
  ```
  :root                         { --auto:#7fb0e8; }   /* on #101316: ≥4:1  */
  @media (prefers-color-scheme:light){ :root{ --auto:#2464a8; } } /* on light panel */
  :root[data-theme="light"]     { --auto:#2464a8; }
  :root[data-theme="dark"]      { --auto:#7fb0e8; }
  ```
- The glyph and marker use `--auto` at **full opacity for the mark, tint via a
  solid 2px inset bar** rather than a faint alpha fill — solid reads in daylight;
  alpha does not.

### ARIA / announcements

- **`aria-label` gains the automation state:** `paramControl()`'s label becomes
  e.g. `"gain, automated, sine LFO"` / `"gain, automated, mixed"`. This is the
  primary non-visual "automated" signal and it costs nothing.
- **Never** put the moving value in an `aria-live` region — it would chatter every
  tick and is a textbook screen-reader denial-of-service. The live value stays on
  `aria-valuenow` / the `<output>` (readable on demand), `aria-hidden` on the
  purely decorative marker.
- **One polite announcement on take-over:** a single `aria-live="polite"`
  utterance, `"gain automation stopped, set to 0.62"`, then silence. This is the
  a11y equivalent of the dying animation.
- **Motor:** the marker overlay is `pointer-events:none` and lives *behind* the
  native input; the 44px hit target is untouched, so automation never makes a
  control harder to grab — the take-over gesture stays as easy as any other drag.

---

## 5. Edge states (mixed / offline / muted / stop)

- **Mixed aggregate:** required honest static state — slashed glyph, `auto·mixed`
  text, existing `.mixed` dashed bar, **no moving marker**. Extends
  `aggregateValue().mixed`, does not fork it.
- **Offline / unbound:** the contract stores the catch-up **constant**, not an
  animation frame. So an offline automated control shows the **glyph (dimmed) and
  the stored value, and does not animate.** Animating an offline box would be a
  lie about liveness — forbidden. Reuse the existing `empty-group`/offline dimming
  (`opacity:.72`).
- **Muted (device/fleet):** mute is a downstream output kill (§6 of the
  contract); it does **not** stop the generator. So the automation indicator and
  motion are *unchanged* by mute — the value genuinely is still moving, silently.
  I deliberately keep them independent rather than freezing motion on mute, so
  the operator's mental model ("mute is downstream of automation") stays true.
  Flagged as an open question for Bob in §7 in case he'd rather see stillness.
- **`stop` generator:** freezes at current output → the address is now a plain
  constant. Treatment: the frozen glyph `▪` flashes once (or, reduced-motion,
  appears then), then the whole automated treatment **clears** — because on the
  wire it *is* now just a constant, indistinguishable from a hand-set value. No
  permanent "was automated" badge; that would be phantom state.

---

## 6. What I deliberately do NOT draw

- **No per-control live oscilloscope / scrolling waveform.** Unaffordable at 40
  controls (§4 budget) and it is the design this reality-check exists to stop.
- **No time-domain waveform painted along a slider's value track.** Category
  error (§1); the axes conflict.
- **No animated/flickering checkbox.** Flicker is a hazard and conveys nothing.
- **No motion as the sole "automated" signal.** Offline, reduced-motion, and
  daylight each defeat it; the static glyph is the source of truth.
- **No continuous `aria-live` value stream.** Screen-reader hostile.
- **No full sparkline on every dense live row.** The real curve is reserved to the
  single-focus Show inspector.
- **No black-only low-alpha wash.** Dies in daylight, inverts on the coming light
  theme.
- **No sixth-decimal shape distinctions on 15–18px widgets** (sine vs tri): two
  glyph families, not six.

---

## 7. Risks & open questions

**The constraint most likely to kill the other experts' designs** (state it
plainly, because it is the crux): *on a Pi-class tablet, a screen of ~40
per-control animated waveforms cannot hold frame — 40 canvases × ~60 fps is
700–2400 ms of work per wall-clock second — and even if it could, a time-domain
waveform on a slider is a value-axis/time-axis category error.* Any proposal whose
"app-wide waveform" is a live picture *per control* is dead on both counts. The
only affordable per-control motion is the value marker itself (paint-once shape,
shared ≤20 fps clock, visible-only); the real waveform picture must be scoped to
the single-focus Show inspector.

Other risks / opens:

1. **Shared-clock API from automation-3.** This design assumes one shared rAF
   value-compute tick. If automation-3 built per-control timers, that must be
   reconciled — my frame budget depends on *one* loop + IntersectionObserver.
2. **`--auto` hue vs a light theme that doesn't exist yet.** I propose values, but
   the light-theme token set is unbuilt; coordinate so `--auto` lands with it and
   passes ≥4:1 on both grounds. Don't ship a dark-only alpha wash as a stopgap.
3. **Muted-but-still-moving.** I keep motion under mute (honest to the downstream
   model). Bob may prefer stillness on mute for calm — a one-line decision.
4. **Int-crossing honesty.** The contract floors-and-emits ints at crossings. The
   visible marker should snap to the **emitted floored value** (what actually went
   on the wire), not the smooth underlying generator, or the display lies about
   what the fleet received. Minor but worth pinning.
5. **Glyph vs screen-reader duplication.** The glyph is `aria-hidden`; the state
   rides in `aria-label`. Verify no double-announcement in the Playwright a11y
   pass.
6. **Show-inspector ownership.** The one real waveform SVG overlaps `automation-2`
   territory; decide which stitch draws it so it isn't built twice.

---

## 8. One-line summary

Make "automated" a static, mandatory, theme-portable **kind glyph** (announced,
daylight-safe, reduced-motion-safe), let the already-computed **value marker** be
the only motion — one shared ≤20 fps clock, visible controls only, thumb/number
sweep on a paint-once track — reuse the ratified CSS-progress mechanism for
fades, keep offline/mixed honestly still, and reserve the one real drawn
waveform for the single-focus Show inspector; anything that animates a waveform
per control dies on the Pi-class tablet's frame budget and on the slider's
value-vs-time axis conflict.
