# Ruling — waveform visualisation UX (automation-4)

Judge-synthesizer, 2026-07-20. Reviewed under Bob's pre-ratification: this is
the ratified design for the app-wide automation treatment. I read the three
expert files, the ground truth, and grounded every load-bearing claim against
`facilitator.js` (`paramControl`/`paramTree`/`liveCard`, the `interacting`
guard, the `send()` path), `facilitator.css`/`style.css` tokens and the
`cue-lead` / `show-step-progress` / `show-step-armed-pulse` precedents,
`docs/OSC-CONTRACT.md` §3.2, `show.js` `parseParamArgs`/`renderParamBuilder`,
`python/paramgen.py`, and the `automation-3` instructions. I did not take the
experts on faith; where they diverge from the code I say so below.

---

## 1. Adjudication of the load-bearing claims

**(a) "Per-control animated waveforms blow the tablet frame budget."** — TRUE,
but only for the *canvas oscilloscope* strawman. calm-ops's own budget table
concedes the shared-clock marker approach at **< 0.5 ms/frame**. The real
choice is not "animate vs don't" but *which cheap mechanism*: pure declarative
CSS (compositor, zero per-frame JS) vs a shared ≤20 fps rAF value loop. Verified
against the house precedents: `cue-lead` and `show-step-progress` are
**pure-CSS keyframes seeded from a CSS custom property, zero JS per frame**,
each with a `prefers-reduced-motion` kill block. That is the ratified pattern
(the culture retired per-frame DOM re-render in `7162943`), and it is strictly
cheaper and more phase-accurate than a rAF loop **for any value that is a pure
function of the clock**. So the rAF loop is unnecessary in the default path.

**(b) "Phase-anchored pure-CSS animation can honestly represent each generator
kind."** — TRUE for `sine`, `tri`, `saw`, `square`, `fade`, `loop`; **FALSE for
`sh` and `drift`**, and this is the sharpest correction to *both* drawing
experts. In `paramgen.py`, `sine/tri/saw/square` and `fade/loop` are pure
deterministic functions of the synced leader clock (`_leader_now` uses the sync
offset; `_shape(frac,curve) = frac**(2**curve)`). The dashboard already has the
identical parse model in `show.js` and can reproduce these exactly, phase-locked
via `animation-delay: calc(-1 * elapsed)`. But `sh`/`drift` values come from

```python
seed = "{identity}|{shape}|{min}|{max}|{period_ns}|{cycle}"
random.Random(seed).uniform(min, max)
```

— a CPython-seeded Mersenne-Twister draw per cycle. It is *deterministic on the
device* yet **not reproducible in JS** (it would require porting CPython's
string→MT seeding and `uniform`), and the emitted values are **never echoed to
the dashboard** (zero-OSC; state carries only the last-sent generator plus the
catch-up constant). Therefore the dashboard has **no knowledge of `sh`/`drift`
values at all — not the future, and not even the past.** motion-dataviz's "past
drawn solid (we saw them)" is factually wrong: the dashboard never saw them.
Ruling consequence: `sh`/`drift` get the static kind-glyph and **no value
marker whatsoever** — no fabricated trace, no "dashed future" chart (chart
furniture at this density is illegible anyway). `free` LFOs know shape+period
but not phase (`random.random()`), so they animate the shape at the true rate
but must be marked *free / not fleet-phase-claiming*.

**(c) "A slider's value axis conflicts with a waveform's time axis."** — TRUE,
and decisive. Painting value-over-*time* along a track whose length already
*means* the value range is a category error (calm-ops #1). This kills
motion-dataviz's "lane as track underlay" and any scrolling waveform in the
track. The honest resolution: the only thing that moves on a slider is a
**single marker on the value axis** — horizontal position maps to the current
computed value, which is exactly what a slider position *means*. That is not a
time-domain waveform; it is the value, drawn where the value belongs.

**(d) "Reuse the ratified CSS-progress precedent (7162943) and the
mixed/offline affordances."** — Verified and adopted. `show-step-progress` (a
CSS `width` grow) is the exact mechanism for an in-flight **fade** (a fade *is*
a progress bar toward a target). The `.mixed` affordance (`opacity:.64` +
centre-tick gradient, indeterminate checkbox, `placeholder="mixed"`) is the
existing honest "no single value" state and mixed-*automation* extends it
rather than forking it. `interacting=true` already freezes `renderCards()` for
range inputs (`facilitator.js` 164/212) — the take-over drain hangs off that.
One implementation gap to close: the `interacting` guard is set only for
`input[type=range]`, not checkboxes; take-over on an automated checkbox must add
the drain class directly.

**(e) Native range thumbs cannot be CSS-animated.** The experts glossed this.
`input[type=range]`'s thumb tracks `.value`, which CSS cannot animate, and
writing `.value` per frame needs a JS loop *and* fights the `interacting`
guard and jitters under the finger. So the value marker is a **separate
`pointer-events:none` overlay** translated by CSS `transform` over the track;
the native input stays fully interactive at its 44px hit target underneath.
This is buildable, keeps the take-over gesture as easy as any drag, and is the
concrete form of "the control is the playhead."

---

## 2. The crux

Two decisions everything hinges on:

**Crux 1 — What carries "this is automated"?** Motion cannot: offline devices
hold a stored constant and must not animate; reduced-motion users get none;
daylight on a tablet washes low-alpha motion out; mixed aggregates have no
single phase to move. Therefore **"automated" is a static, mandatory,
theme-portable, screen-reader-announced mark. Motion is enhancement layered on
top, only where it is honest and affordable.** All three experts actually
converge here once cornered (even perf-instrument's reduced-motion fallback is
"static glyph + AUTO tag").

**Crux 2 — How does the honest motion run?** **Declarative per-control CSS,
phase-anchored by a negative `animation-delay` seeded from the synced clock —
no rAF value loop at all in the default path — and only on the value axis
(a marker, never a time-domain waveform on the track).** This is cheapest,
phase-accurate, reduced-motion-trivial (one media block), and dodges the axis
conflict. It runs only for the kinds the dashboard can actually compute.

Everything else is styling of those two decisions.

---

## 3. The ruling — one app-wide treatment, in three layers

A three-layer model, in strict cost/reliability order. Layer 1 is mandatory and
static; each layer up is more motion and more optional. This is calm-ops's
spine, executed with perf-instrument's "the control is the playhead" and
motion-dataviz's "one primitive, shape-is-geometry, deterministic-futures-only"
discipline — but with the drawn *lane* rejected and the value-axis marker
adopted in its place.

### Layer 1 — Kind glyph (static, always, the source of truth)

A monochrome kind glyph rendered in the `.live-param` label (`<span>` slot),
in a new semantic token `--auto`. It is `aria-hidden`; the state rides in
`aria-label`. It survives offline, reduced-motion, daylight, and the coming
light theme because it never moves and never relies on alpha.

Glyph vocabulary — **two LFO families, not six** (at 15px, sine-vs-tri buys
nothing; the exact shape lives in the Show inspector):

```
  constant / not automated  →  no glyph (a static value is the absence of automation)
  sine / tri / drift LFO     →  ∿   (smooth family)
  saw / square / sh LFO      →  ⌁   (stepped family)
  fade (in flight)           →  ╱   (clears to none on completion)
  loop                       →  ⟳
  stop / frozen              →  (drains to none — a stop is just a constant)
  mixed automation           →  ∿̸  + text "auto·mixed"
```

### Layer 2 — Track / shape state (static, paint-once)

For an **automated slider**, the track carries a paint-once `--auto` state cue
(a 2px inset bar / tint set once on generator change — a solid mark, never an
alpha wash, so it reads in daylight and inverts correctly on light theme). This
says "automated" on the control itself without drawing a curve on the value
axis. A **fade** additionally reuses `show-step-progress` verbatim: a single
CSS `width` grow toward the target, `var(--show-progress-duration)`-style, with
the existing reduced-motion kill. Zero JS. When the fade completes it becomes a
constant and the whole treatment clears.

### Layer 3 — Value marker (motion, budgeted, deterministic kinds only)

A `pointer-events:none` overlay marker (a 3–4px `--auto` dot / 2px bar) sitting
over the slider track, translated along the **value axis** by a pure CSS
keyframe:

```css
transform: translateX(var(--auto-pos));           /* value → 0..100% of track */
animation: auto-<shape> var(--auto-period) linear infinite;
animation-delay: calc(-1 * var(--auto-elapsed));  /* fleet-phase anchor */
```

- One `@keyframes` per shape (`auto-sine` sampled points; `auto-tri` linear
  up/down; `auto-saw` ramp+reset; `auto-square` two-step). `min`/`max` map to
  the translate range via custom props. Period = duration; phase = negative
  delay from the synced clock (§3.2 `((t/period)+phase) mod 1`, resend-safe).
- `fade`/`loop`: a finite / tiled keyframe; loop **snaps** at the seam (instant
  jump, never a tween — honest to §3.2 "snapping back"). Fade fires
  `animationend` → drop to plain.
- `curve c:<n>` bends the ramp via keyframe easing where legible; degrade to a
  straight segment in dense rows without dishonesty (the curve is a nuance, not
  a state).
- `sh` / `drift`: **no marker.** Glyph only. The dashboard cannot know the
  values (§1b). Marker parks at / is omitted for the catch-up constant.
- `free` LFOs: animate shape+period, seeded from a local arbitrary phase,
  visibly marked *free* (hollow marker) — the shape/rate is honest, the phase
  is explicitly not claimed.

**No rAF loop ships in the default path.** If Bob later wants a live *number*
(not just the target), add one shared ≤4 Hz `setInterval` over
visible-and-automated `<output>`s (IntersectionObserver-gated) as a separate
follow-up — never rAF, never all rows, never per-frame digits.

### Per control type

| Control | Layer 1 glyph | Layer 2 shape | Layer 3 marker |
|---|---|---|---|
| **Slider** (`range`+`output`) | yes, in label | tint; fade = CSS-progress | value-axis overlay marker (deterministic kinds); `sh`/`drift` none |
| **Checkbox** (int 0..1) | yes | static `--auto` ring on box (**not** pulsing) | none — box reflects current floored value on state push; **no flicker** |
| **Numeric / output-only** | yes | none | none by default; `<output>` shows target (fade) or the static catch-up value + kind. No per-frame digit tick |
| **Text (`type:"s"`)** | **never** | — | — | strings are not automatable (§3.2). Silence is information |

### Aggregate rows (All / Group)

`aggregateValue()` already returns `{value, mixed}`. Extend it to also compare
the per-Seat *generator*. A moving marker is a truth-claim about one phase, so:

- **Uniform generator + phase across members** → render exactly as the
  single-control case (honest: every member truly runs it).
- **Different generators (or phases)** → `∿̸ auto·mixed`, the existing `.mixed`
  static bar, **no marker motion, no invented shape.** Take-over still seizes
  all members to one constant and drains the same way.

### Offline / muted / stop

- **Offline / unbound** → glyph present but **dimmed**, marker **frozen** at the
  stored catch-up constant, no animation. Reuse existing `.offline` dimming. A
  moving offline fader is a lie about liveness (§3.2, ground truth).
- **Muted (device)** → automation still runs on the device, so the marker
  **keeps moving**, desaturated toward `--dim`; the `.device-mute-indicator`
  coexists (orthogonal). *(One-line open question for Bob: he may prefer
  stillness-on-mute for calm; all three experts flag it. Default = keep moving,
  honest to the downstream model.)*
- **`stop`** → freezes at current output, which on the wire *is* a plain
  constant. Treatment drains exactly like a remote take-over (§ below) and
  clears to plain. **No persistent "was automated" badge** — a distinction
  without an operational difference; it would clutter every settled control.

### Take-over — the animation dying under the finger

On `pointerdown` on an automated range/checkbox:

```
t=0     add .taking-over to this .live-param (renderCards already frozen via
        interacting for range; set the class directly for checkbox).
t=0     animation-play-state: paused  → marker stops dead where it is.
0→180ms ring/tint/glyph drain (opacity + collapse; single-element CSS
        transition, no per-frame work). Number, if any, follows the finger.
drag    normal slider drag — marker is pointer-events:none, never fought for
        the pointer.
release send() fires a plain value (existing set_live_param path) → constant →
        automation dead on the device too. Glyph stays gone.
```

The persistent evidence is the glyph *disappearing* (a static change a
low-vision operator can verify after the fact) plus one polite ARIA
announcement — "the animation died" is the sugar, the state change is the
substance. Under reduced-motion the drain is replaced by instant clear.

### Reduced-motion story

Mirror the house pattern (`facilitator.css` 52, `style.css` 42/50): a single
`@media(prefers-reduced-motion:reduce)` block sets `animation:none` /
`animation-play-state:paused` on every marker and drops the take-over drain to
an instant clear. **The static kind-glyph carries the entire indicator**, which
is exactly why Layer 1 had to be static and mandatory. Nothing essential is
lost; nothing oscillates.

### Theme portability (light theme coming)

Introduce **one** new semantic token, `--auto`, distinct from `--green`
(value/online), `--red` (mute/danger) and `--amber` (**already means crashed —
do not reuse**). A calm blue in the family the Show pills already use.
Themed from day one off both the media query and the anticipated `data-theme`
attribute:

```css
:root                                { --auto:#7fb0e8; }  /* ≥4:1 on #101316 */
@media (prefers-color-scheme: light) { :root{ --auto:#2464a8; } }
:root[data-theme="light"]            { --auto:#2464a8; }
:root[data-theme="dark"]             { --auto:#7fb0e8; }
```

Marks are **solid** (glyph, 2px inset bar, marker dot), never low-alpha washes
— alpha dies in daylight and inverts wrong on white. Everything routes through
tokens / `currentColor` so the theme flip is free. *(I overrule
perf-instrument's "reuse `--green` for running": green already conflates
online/value with automated; a dedicated hue is clearer, colour-blind-kinder,
and costs one token.)*

### ARIA

- `paramControl()`'s `aria-label` gains the automation state:
  `"gain, automated, sine LFO"` / `"gain, automated, mixed"`. This is the
  primary non-visual signal and costs nothing.
- The marker and glyph are `aria-hidden`; the live value stays on
  `aria-valuenow` / `<output>` (readable on demand).
- **Never** stream the value into `aria-live` (screen-reader DoS).
- **One** `aria-live="polite"` utterance on take-over: `"gain automation
  stopped, set to 0.62"`, then silence.
- Marker overlay is `pointer-events:none` behind the native input; the 44px hit
  target is untouched.

### Show tab / inspector

The Show message inspector (`renderParamBuilder`, `automation-2` territory) is
the **one** surface that may draw a real value-over-time curve — single-focus
authoring, room, and time genuinely *is* the x-axis there. Default a **static**
SVG path of the generator being authored (≤2 cycles), redrawn only on edit; at
most one on screen. A slow demo playhead is opt-in and dies under
reduced-motion. It visualises the *message being authored*, which runs on no
device, so it anchors to **no** clock. **Ownership: this SVG belongs to
`automation-2`'s builder, not this stitch** — flag so it isn't built twice; the
Show step rows themselves get no automation animation.

---

## 4. What I reject and why

- **A drawn "automation lane" / track-underlay waveform per generator kind**
  (motion-dataviz core) — value-axis/time-axis category error on the slider
  (§1c), chart furniture illegible at 10–14px, and it forces `sh`/`drift` to
  either lie or draw dashed-unknown chart marks the dashboard has no data for.
- **`sh`/`drift` "past solid, future dashed"** — the dashboard never saw the
  past and cannot compute it (§1b). Glyph only.
- **A shared rAF value loop as the default motion engine** (calm-ops) —
  unnecessary for clock-pure kinds; pure CSS is cheaper and phase-accurate.
  rAF/interval returns only as a gated ≤4 Hz *number* follow-up if Bob wants it.
- **Pulsing ring / blinking dot on checkboxes** (perf-instrument, motion-dataviz)
  — flicker is a vestibular/seizure hazard and conveys nothing a static ring
  doesn't. Static `--auto` ring only.
- **Reusing `--green` for "running automation"** — overloads online/value; use
  the dedicated `--auto` token.
- **A persistent "was automated / frozen by stop" badge** — phantom state; a
  stopped generator is a constant.
- **Any waveform on strings** (§3.2 reserves the grammar off strings).
- **Canvas anywhere in the default design** — reserved only as a future escape
  hatch if an approved `sh`/`drift` history feature ever justifies it (one
  shared, ≤10 fps, gated).

---

## 5. Implementation plan — smallest first slice first

**Slice 1 (MVP, ship first): the static source-of-truth layer, no motion.**
- Add the `--auto` token (dark + light + `data-theme`) to `style.css`.
- `paramControl()`: when the tracked last-sent generator for a
  `(scope, identity)` is non-constant, inject the kind glyph in the label and
  extend `aria-label` with the automation state; strings never get it.
- Extend `aggregateValue()` to compare generators → honest `auto·mixed` static
  state reusing `.mixed`.
- Offline → dimmed glyph, no motion. Take-over clears the glyph + fires one
  polite ARIA announcement.
- This alone is fully a11y-complete, daylight/offline/reduced-motion-safe, and
  satisfies `automation-3`'s "minimal placeholder." Independently valuable.

**Slice 2: Layer 2 + Layer 3 on the slider.**
- Paint-once `--auto` track tint; fade = `show-step-progress` reuse.
- Value-axis overlay marker with per-shape `@keyframes` + negative-delay phase
  anchor, for `sine/tri/saw/square/loop`; `sh`/`drift` stay glyph-only; `free`
  marked. Take-over freeze-then-drain (extend the `interacting` guard to
  checkboxes). Reduced-motion block.
- Re-anchor `--auto-elapsed` on the existing `ws.on("state")` ticks (cheap
  periodic re-seed, zero extra OSC) to bound CSS-clock drift; debounce so only
  meaningful phase error re-seeds.

**Slice 3: numeric/output polish + Show inspector static preview**
(coordinate the preview SVG with `automation-2`; optional ≤4 Hz number tick
behind a preference, gated).

## 6. Verification sketch (house Playwright pattern)

Copy the newest tied `verify_*.py`; repo-by-marker root, sim ports, venv
`~/.venvs/bopos`, headless chromium, teardown. Drive real `dashboard/server.py`
+ `tools/simfleet.py` on non-default ports. Assert:

1. Send an `lfo sine …` generator → the `.live-param` gains the glyph and
   `aria-label` contains `automated, sine` (lowercase before matching the
   `capitalize`d row).
2. **Zero-OSC**: while the marker animates, assert the outgoing OSC/console shows
   no `set_live_param` frames (animation is local simulation).
3. **Take-over**: `pointerdown` + drag + `pointerup` emits exactly **one** plain
   value and removes the glyph/marker (`window.scrollTo(0,0)` and re-read
   bounding boxes before the drag; clamp on-screen; single type-aware
   `page.on("dialog")` handler).
4. **Offline** seat → glyph present, marker has no running animation
   (`getComputedStyle(...).animationPlayState !== "running"` or class absent).
5. **Mixed** aggregate over differing generators → `auto·mixed`, no marker.
6. **Reduced-motion**: `page.emulate_media(reduced_motion="reduce")` → no marker
   animation, glyph still present, take-over clears instantly.
7. **`sh`** generator → glyph present, **no** value-marker element rendered.

Pass `wait_for_function` args as `arg=value` (keyword-only, sync API).

---

## 7. One-line ruling

"Automated" is a **static, mandatory, theme-portable kind-glyph** (announced,
daylight/offline/reduced-motion-safe, in a new `--auto` token); the only motion
is a **pure-CSS value-axis marker phase-anchored to the synced clock**, run for
the deterministic kinds only (`sine/tri/saw/square/fade/loop`) and **never** for
`sh`/`drift` (the dashboard cannot know their values) — no rAF, no drawn lane,
no time-axis waveform on the slider, no flicker on checkboxes — dying under the
finger via freeze-then-drain, with the drawn curve reserved to the single-focus
Show inspector.
