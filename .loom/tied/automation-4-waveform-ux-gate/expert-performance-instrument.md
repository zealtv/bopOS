# Waveform visualisation — performance-instrument lens

Lens: pro-audio / performance-instrument interaction (Ableton, TouchOSC,
hardware surfaces). Mandate: make an automated control read as **live
instrument state** mid-performance, and make take-over *feel* like grabbing
a moving fader — the motion dies under your finger.

---

## 1. Altitude & framing

I design at the **control level, not the badge level.** The strongest thing
this UI already has going for it is that a slider is a fader and a checkbox is
a mute button — physical objects. So the automation treatment should not be a
new decorative widget bolted next to the control; it should make the *existing
control move on its own*, the way a motorised fader moves. That is the whole
point of "the animation dying under your finger": you have to be able to grab
the thing that is moving.

Three commitments follow, and they're the spine of everything below:

1. **The control is the playhead.** On a slider the *thumb* is what moves; the
   sparkline is a small "what shape" legend, not the primary animation. On a
   checkbox the *box* flips and its ring pulses. We animate the instrument, not
   a chart beside it.
2. **Motion is declarative, phase-anchored CSS — never rAF, never re-render.**
   The generator kind, period, min/max and a *negative* `animation-delay`
   computed from the shared synced clock are pushed as CSS custom properties at
   render time. The browser's compositor runs the loop. This is exactly the
   house precedent — `--cue-lead-duration` (facilitator.js ~197) and
   `show-step-progress` / `show-step-armed-pulse` (style.css line 50). Zero OSC,
   zero per-frame JS, and phase-anchoring falls straight out of the contract's
   "`((t_synced/period)+phase) mod 1`, resend is safe" (§3.2) → set
   `animation-delay: calc(-1 * <elapsed>)` once and the CSS loop lands in fleet
   phase for free.
3. **Take-over feedback is a death animation local to the touched element.**
   `interacting=true` already freezes `renderCards()` (facilitator.js 212), so
   the touched control is safe from re-render. We hang the fade-out entirely on
   a CSS class transition on that one node.

I deliberately keep the palette tiny: reuse `--green` (already the "live/online"
signal — `.dot.online`, `show-state-playing`) for *running* automation, `--dim`
for *frozen/offline*, `--amber` for *mixed/uncertain* (already the badge and
`patch-badge-switching` colour). No new colour language for operators to learn.

---

## 2. Design (with mockups)

### 2.1 The automated slider (the primary case)

```
  Gain                                          ┌ live number, tabular, counting
  ┌──────────────────────────────────────┐  0.62│  ∿ 2.0s   ← generator legend
  │······•═══════════════════════════════│      │  (sparkline + period)
  └──────────────────────────────────────┘
         ▲ thumb = playhead, glowing green,
           driven left↔right by CSS keyframe.
           Faint underlay (··· / ═══) shows the
           shape's travelled vs coming path for
           FADES only; LFO/loop leave the track clean.
```

- **Thumb** carries the motion. A `.auto` class puts a 2px green ring +
  `box-shadow: 0 0 6px var(--green)` on the thumb and animates its position via
  a keyframe bound to `--wave-shape`. The operator sees the fader physically
  riding its LFO — instantly legible as "this is moving, hands off unless you
  mean it."
- **Legend** sits in the existing `<output>` slot (already right-aligned,
  `70px`, tabular — style.css `.params output`). Two lines when room, one when
  dense: the **live value** (already animates because the generator drives it)
  plus a **12×14px sparkline glyph** and the **period/duration** as musician
  shorthand (`2.0s`, `↗ 3s`, `↻`). The number is the precise readout; the glyph
  is the "what am I looking at" at a glance across a wall of cards.
- **Track underlay** is used *only for fades* — a green wash of the completed
  portion, identical in spirit to `show-step-progress` (a moving `width`). LFOs
  and loops get **no** track fill; a persistent full-track ripple at Ableton
  density across dozens of rows is visual noise. The moving thumb alone says
  "cyclic."

### 2.2 The automated toggle (int 0..1)

A 0..1 param can only be driven by a square LFO, an S&H, or a fade that snaps.
A checkbox can't show 0.5, so we don't pretend:

```
   Bypass   ⊡          Bypass   ☑          Bypass   ☐
            └ pulsing            └ box is    └ box is
              green ring           actually    actually
              = "driven",          checked      unchecked
              flips at the         right now    right now
              crossings
```

- A `.auto` pulsing ring around the box (reuse `show-step-armed-pulse`'s
  border-pulse keyframe, retinted green) says "automation owns this."
- The box's checked state flips at the real integer crossings the generator
  produces — on render, honestly. No intermediate fakery.
- For a **fade on 0..1** (effectively instant snap) we still show the ring for
  ~1s of grace so the operator registers "that flip was automation, not a
  ghost," then it clears.

### 2.3 Numeric-only / output-only readouts

Same legend as the slider (sparkline glyph + counting number), minus a thumb
to move. The glyph carries the motion via a small translating playhead dot.

### 2.4 String controls

**Nothing. Ever.** §3.2 reserves the grammar off strings; a string control
never shows a waveform, a legend, or a ring. This silence is itself
information: no motion == not automatable.

### 2.5 The generator vocabulary (what each kind draws)

12×14px sparklines, stroke `var(--green)` at running contrast, `var(--dim)`
when frozen. The playhead is a 2px dot riding the shape via CSS.

```
 constant   (no badge at all — a static value is the absence of automation)

 fade       ╱•          one-shot: playhead crosses once, L→R, over <dur>,
            ╱            then the badge DISSOLVES to plain (fade → constant).
                        segment-list = a polyline of the segments.

 loop       ╱╲╱╲ ↻      the segment polyline, playhead loops, SNAPS back to
                        start at the seam (a visible 1-frame jump — honest to
                        "snapping back to its start", §3.2).

 lfo sine   ∿  •        smooth loop, phase-anchored to fleet clock.
 lfo tri    ◺◹          linear up/down, c:<n> bends the ramp.
 lfo saw    ⋰|          ramp then vertical reset.
 lfo square ⊓⊔          hard steps; on a 0..1 toggle this is the box-flip.
 lfo sh     ⌐_¬         stepped random plateaus (sample-and-hold).
 lfo drift  ∼∼∼         soft wandering line, no fixed period feel.

 stop       ─           flat held line. See §5 — its "look" IS the death
                        animation: the shape flattens and the badge fades,
                        because the end state is just a static value.
```

`f` (free-phase) LFOs get a tiny hollow dot on the glyph instead of filled —
"decorrelated, not fleet-locked." `c:<n>` curve just bends the drawn ramp; no
extra chrome.

---

## 3. Per-surface treatment table

| Surface | Control | Indicator location | Motion carrier | Notes |
|---|---|---|---|---|
| Facilitator live-param slider; editor & seat-detail sliders | range + output | **thumb = playhead** (green ring); sparkline + period + live number in `<output>` | CSS keyframe on thumb pos from `--wave-*`; fades add `show-step-progress`-style track wash | primary case |
| Live-param toggle (int 0..1) | checkbox | pulsing green ring on box; box flips at real crossings | `show-step-armed-pulse` retinted; state on render | no intermediate fakery |
| Numeric / output-only | `<output>` | sparkline glyph + counting number | small playhead dot on glyph | no thumb to move |
| String text input | — | **none, ever** | — | §3.2 reserves grammar off strings |
| All / Group row, **uniform** generator across members | underlying control | exactly as the single-member control | same | aggregate is honest = one shape |
| All / Group row, **mixed** generators | whole `.live-param` | neutral **`~ mixed auto`** amber chip; slider goes indeterminate (no thumb ride, no single shape) | one slow shimmer, no specific waveform | never draw a shape you can't justify |
| Offline / unbound | any | **static, dimmed** shape glyph; thumb parked at catch-up constant; ring not pulsing | **no motion** | see §5 |
| Muted device | any | motion continues but **desaturated to `--dim`**; mute glyph coexists | CSS, low contrast | automation still runs on device |
| Show inspector (builder) | preview pane | a single **static** shape SVG of the args being built (optional slow demo loop) | one preview element only | authoring aid, not a live control |

---

## 4. Motion & interaction spec

### 4.1 How it runs (the cheap engine)

At render, each automated `.live-param` gets data/CSS props:

```
--wave-shape: <keyframe-name>;   /* sineWave | triWave | fadeOnce | ... */
--wave-period: 2s;               /* LFO period or fade dur, in real units */
--wave-delay: -0.74s;            /* = -(elapsed within period), from synced clock */
--wave-min / --wave-max;         /* maps generator range → thumb 0..100% */
```

The thumb keyframe is `animation: var(--wave-shape) var(--wave-period) linear
infinite; animation-delay: var(--wave-delay);`. LFOs loop; fades are one-shot
(`fadeOnce` + `animation-fill-mode: forwards`) with an `animationend` listener
that drops the badge to plain. **This is the only JS the animation needs.** No
rAF, no interval, no OSC — the compositor and the shared clock do the work,
which is precisely why the contract made LFOs clock-anchored and idempotent.

Contrast/size at density: sparkline **12×14px**; thumb ring **2px + 6px glow**;
running stroke `--green`, frozen `--dim`, mixed `--amber`. On the anticipated
light theme, glow-on-black won't carry — so the *shape stroke* (not the glow)
is the load-bearing signal, with a 1px contrasting outline; the glow is pure
enhancement. Nothing reads only on `#101316`.

### 4.2 Take-over — the fader dying under your finger

Sequence on `pointerdown` on an automated range/checkbox:

```
  t=0ms     finger lands. renderCards() is already frozen (interacting=true).
            add class .taking-over to THIS .live-param.
  t=0ms     animation-play-state: paused  → the thumb stops dead where it was.
  0→180ms   the green ring collapses inward + fades (transition on box-shadow,
            border-color, opacity); the sparkline flatlines then dissolves;
            the period text fades. The number stops counting and follows finger.
  drag      normal slider drag — the animation never fought for the pointer
            (playhead was CSS transform/pos, pointer-events stay on the range).
  pointerup send() fires a plain value (existing path, facilitator.js 260) →
            constant → automation is dead on the device too. Badge stays gone.
```

The felt experience: you touch a moving fader, it *goes still under your
thumb*, the glow drains out — unmistakable "I just took manual control."
Matches the contract exactly: touching sends a plain value which replaces the
generator. Because take-over is local-CSS and render is frozen, there is no
flicker, no fight, no re-grab. The 180ms drain is short enough to feel causal
(you did that) and long enough to *see* (not a jump-cut).

Crucially the animation **must not steal the pointer** even before take-over:
the playhead is drawn on the thumb/pseudo with `pointer-events:none`; the real
`<input type=range>` hit target is unchanged and full-size. On a tablet the
moving thumb is never harder to grab than a static one.

### 4.3 Reduced motion & distraction budget

`@media (prefers-reduced-motion: reduce)` (already respected at style.css 42,
50): freeze every playhead, show the **static** shape glyph + a small `AUTO`
tag, keep the number readout (throttled). The operator still knows what's
automated and its shape; nothing oscillates. Take-over still drains (a single
short opacity fade is within vestibular budget) or, to be safe, snaps.

---

## 5. Edge states

### 5.1 Mixed aggregate (different per-Seat generators)

An All/Group row over members running *different* generators must not invent a
waveform. It renders a neutral honest state:

```
  Gain            ~ mixed auto        ◐  ← indeterminate slider, no thumb ride
                  └ amber chip, one slow shimmer, NO shape
```

Reuses the existing `mixed` affordance (facilitator.js 79-85, indeterminate
checkbox / `placeholder="mixed"`) plus one shimmer to say "and they're moving."
Touching it still takes over *all* members to one constant — the shimmer drains
the same way. Uniform-generator aggregates instead show the real shared shape:
that's honest because every member truly runs it.

### 5.2 Offline / unbound

Durable stored value survives; §ground-truth is explicit that the stored value
is the **catch-up constant, not a stale animation frame.** So offline controls
**do not animate.** The thumb parks at the stored value, the sparkline is drawn
**static and dimmed to `--dim`**, no ring pulse. Visually reads as "this would
be moving, but the device isn't here" — the same dimming grammar as
`.offline` / `.node.offline` already in the app. Never animate a control whose
device can't confirm the phase; a moving offline fader is a lie.

### 5.3 Muted (device mute)

Mute silences *audio*, not automation — the generator is still running on the
device. So the waveform **keeps moving**, but desaturated to `--dim` and the
mute glyph (`.device-mute-indicator`) coexists unchanged. Reading: "still
automating, currently silent." Un-mute and the motion snaps back to green.
This is the instrument-correct behaviour — a muted channel whose LFO is still
sweeping is normal studio life; freezing it would misrepresent device state.

### 5.4 Stop

`stop` freezes at current output. Its *appearance is the death animation*: the
shape flattens to a held line and the badge dissolves to a plain static value —
because on the wire and to the operator, a stopped generator and a hand-set
constant are the **same terminal state** (a static value, take-over-able).
I deliberately do **not** invent a persistent "frozen by stop" badge distinct
from a plain constant; that's a distinction without an operational difference
and it would clutter every settled control. Remote `stop` therefore looks like
someone else did your take-over: the same 180ms drain, from afar.

---

## 6. What I deliberately do NOT draw

- **No full-track LFO ripple / scrolling waveform inside slider tracks.** At
  Ableton density across dozens of cards it's noise, and it fights the mixed and
  progress affordances that also live in the track.
- **No per-generator colour coding.** Green=running, dim=frozen, amber=mixed.
  Shape carries kind; colour carries *liveness*. Operators already read
  green/dim/amber everywhere.
- **No persistent "was automated" history / trails after take-over.** Once you
  grab it, it's yours and clean.
- **No distinct persistent badge for `stop` vs constant** (see §5.4).
- **No waveform on strings, ever** (§2.4).
- **No rAF / canvas / per-frame re-render** as the default path. A tiny
  `<canvas>` is *tolerated* by ground-truth for a few widgets, but I don't need
  it: CSS keyframes + the shared clock cover every kind. Keep it off tablets'
  main thread.
- **No animated Show-tab step rows** for automation — the Show inspector shows a
  *static* preview of the args being authored; the live motion belongs on the
  live controls, not the sequencer document.

---

## 7. Risks & open questions

1. **Clock drift vs CSS anchoring.** `animation-delay` anchors phase at render
   but the tab's CSS clock then free-runs; over minutes an LFO could visibly
   drift from the fleet. Mitigation: re-stamp `--wave-delay` on the existing
   state pushes (heartbeats/`ws.on("state")`), which already arrive regularly —
   a cheap periodic re-anchor, still zero extra OSC. Needs a decision on
   re-anchor cadence (I'd tie it to state ticks, not a new timer).
2. **`sh` / `drift` are random per device.** The dashboard can't know the
   device's actual random sequence, so its sparkline is *representative*, not
   sample-accurate. I think that's fine (the glyph says "S&H", not "these exact
   values") but Bob should confirm we're OK showing an honest-but-not-literal
   shape for the two random shapes.
3. **Fade `animationend` reliability.** If the tab is backgrounded mid-fade the
   `animationend` may fire late; the next state render must reconcile (badge →
   plain from stored value). Low risk, worth a test.
4. **Light theme, unshipped.** I've kept the shape stroke (not glow) load-
   bearing, but the amber "mixed" chip and green ring want a real check once the
   light tokens exist. Don't hard-code the shadow alphas.
5. **Take-over drain vs reduced-motion.** 180ms opacity fade should be within
   budget, but if the a11y lens disagrees, snap instead — the *functional*
   feedback (ring gone, value static) survives either way.

---

## 8. One-line summary

Make the control itself the playhead — a motorised fader that rides its
generator via phase-anchored CSS (zero OSC/rAF), carries a 12px shape+period
legend, and *dies under your finger* in a 180ms drain that is literally the
take-over — with green=running, dim=frozen/offline, amber=mixed, and strings
never touched.
