# Expert lens: data-visualisation & motion designer

Waveform visualisation for automated `/p/*` controls — app-wide treatment.

Grounded in: `facilitator.js` `paramControl`/`paramTree`/`liveCard`/`bindCards`;
`dashboard.js` seat/editor sliders; `show.js` `parseParamArgs` (the canonical
generator model already lives here); `style.css` tokens
(`--panel:#191e23 --line:#303942 --text:#e8edf1 --dim:#8f9ba5 --green:#45d483
--amber:#f2b84b --red:#ff4e5d`, system-ui 15px); OSC contract §3.2.

---

## 1. Altitude & framing

I am designing **one primitive, not eleven pictures.** The temptation with
"waveform visualisation" is to render an oscilloscope per generator kind. That
is the wrong altitude on three counts: it invites per-frame canvas redraws (the
exact cost `7162943` culturally retired), it makes sh/drift lie about a
stochastic future, and it produces a different widget in every control type.

My altitude is a single reusable component I call the **automation lane**: a
thin, ambient, time-axis strip that renders the *known shape* of the generator
**once** as static SVG, and moves *exactly one element* — a playhead — via
**CSS transform seeded from the synced clock**. Everything else is styling of
that one primitive.

The load-bearing insight from the dataviz lens is a **decomposition of the
signal into two layers with radically different update rates**:

| Layer | What it encodes | Changes when | Render tech | Per-frame cost |
|---|---|---|---|---|
| **Shape** (static) | *what kind* of motion (ramp / sine / steps…) | generator message changes (rare) | one inline SVG `<path>`, drawn once | **zero** |
| **Playhead** (dynamic) | *where we are now* in that motion | continuously, but deterministically from the shared clock | one element moved by CSS `transform`/keyframe, GPU-composited | **zero main-thread** |

Because bopos.py hands the dashboard both the generator *and* the synced clock,
the playhead's position is a pure function of time. That means the motion can be
**declarative** — a CSS animation whose phase is seeded by a negative
`animation-delay`, not a JS rAF loop that recomputes and writes the DOM every
frame. This is the single most important cheapness/honesty decision in the
whole design, so I'll state it as a rule:

> **The waveform never re-renders per frame. The shape is painted once; the
> playhead is a GPU-composited transform seeded from the clock. JS runs only on
> generator change and clock resync.**

Everything below serves that rule.

---

## 2. Design (with mockups)

### 2.1 The lane, anatomy

A lane is a fixed-height strip (14px in roomy live cards, 10px in Ableton-
density Show rows). x-axis = time; y-axis = value between the declared
`min`/`max`. It carries at most three marks:

```
 ┌───────────────────────────────────────┐  ← lane box (transparent; no border,
 │            ╭──────────────             │    no axes, no grid, no labels)
 │      ╭────╯                            │  ← SHAPE: static SVG path, stroke
 │ ●───╯                                  │    var(--dim) @ ~0.5 (recedes)
 │ ▏                          ┊ ┊ ┊ ┊ ┊   │  ← PLAYHEAD ● (accent) + a faint
 └───────────────────────────────────────┘    "future" region drawn dashed/dim
     now →                     (upcoming)
```

- **Shape** = `var(--dim)` stroke, ~1px, ~0.5 alpha. Ambient. It must *recede*
  — it is always-on wallpaper, subject to the operator's distraction budget.
- **Playhead** = a 3–4px dot or 2px vertical bar in the accent
  (`--green`), the only element with full contrast and the only thing that
  moves. A soft `box-shadow` glow (the existing `.dot.online` idiom) buys
  daylight legibility without enlarging it.
- **Past vs future**: the segment behind the playhead may be drawn at full
  shape-opacity; ahead of it dimmer/dashed. This reads as "we've done this bit,
  this bit is coming" without any axis furniture.

No ticks, no gridlines, no amplitude numbers, no baseline box. It is a **glyph,
not a chart.**

### 2.2 Per-generator vocabulary

Each generator kind is a different *static path* plus a different *playhead
rule*. The parsed model from `show.js` gives us everything.

```
CONSTANT / plain value   (mode:"value")
   → NOT automated. No lane at all. The control renders exactly as today.
     (A constant is the degenerate generator == the take-over result. Drawing
      a lane here would cry wolf.)

STOP   (mode:"stop")
   ├──────────●──────────┤        flat line at the frozen value.
        ⏸ held                    NO motion. Small ⏸ tag or amber tint.
                                   Honest: "this was automated, now frozen."

FADE — single segment   (mode:"fade", 1 segment)
                 ╭──────  target
        ●───────╯                 a ramp from current→dest. Playhead climbs it
     3.2s left                     once, then the lane RETIRES (control becomes
                                   plain). Curve c:<n> bends the ramp visibly.

FADE — multi-segment    (mode:"fade", segments[])
          ╱╲      ╭────
         ╱  ╲    ╱                 polyline of the segment list from current.
     ●──╯    ╲__╱                   Playhead traverses left→right ONCE, retires
                                    at the end. Future segments ghosted.

LOOP    (mode:"loop", segments[])
    ↺  ╱╲__╱╲__╱╲__                 same polyline, but tiled + a ↺ glyph.
       ●                            Playhead cycles; at the wrap it HARD-SNAPS
                                    back to start (contract: "snapping back") —
                                    show the snap as an instant jump, never a
                                    tween, or you misrepresent the sound.

LFO sine    (shape:"sine")     ╭╮  ╭╮        one–two periods, true sinusoid.
                              ╱  ╲╱  ╲ ●     Playhead sweeps and wraps.
LFO tri     (shape:"tri")     ╱╲╱╲╱╲         c:<n> bends the legs.
LFO saw     (shape:"saw")     ╱|╱|╱|         asymmetric ramp + vertical reset.
LFO square  (shape:"square")  ⊓⊔⊓⊔           two levels; playhead steps.

LFO sh  (sample-hold random, shape:"sh")
       ▁▔▂ ▔  ┊?┊?┊             PAST steps drawn solid (we saw them);
        ●                        FUTURE drawn as dashed "?" tick marks — we do
                                 NOT fabricate a random future we cannot know.

LFO drift  (smoothed random, shape:"drift")
       ‿⁀‿ ╌╌╌?                  PAST wander solid; FUTURE dashed/unknown.
        ●                         Rounded joins signal "smooth", steps signal sh.
```

The honesty line for stochastic kinds is a hard rule, not a nicety:

> **sine/tri/saw/square are deterministic and clock-anchored — we may draw
> their true future. `sh` and `drift` are stochastic — we draw only past and
> present; the future is dashed "unknown". Never render a plausible-looking
> fake trace for a value we cannot predict.**

The *character* (steppy vs smooth) is carried by SVG `stroke-linejoin`
(`miter`/square for sh & square LFO; `round` for sine/drift). That alone
distinguishes the four "wiggle" kinds at 10px without labels.

### 2.3 The slider — where the lane lives

The slider is `<output>` + `<input type=range>` in a `130px 1fr 70px` grid; the
range spans the `1fr`. Put the lane as a **track underlay**: same width and
x-position as the range, sitting *behind* the native track, ~2px above centre.
The range thumb already shows *current value* on the value axis — so on a
slider the lane's job narrows to **"what's coming"**, and the thumb is the
de-facto value marker. We still draw a playhead on the lane's *time* axis for
kinds where the thumb can't express phase (LFOs), but we do **not** fight the
user by writing `input.value` every frame (the existing `interacting` guard
already suspends renders during a grab; per-frame value-writes would also make
the thumb jitter under the finger). The thumb tracks value at a **coarse cadence
or not at all during flight** — the lane owns the motion.

```
 gain            ╭────────────────────────────────╮   0.80
                 │ ░░░░░╱╲╱╲╱╲ lane underlay ░░░░░ │
                 │ ●═══════╫═════ native track ════│   ← thumb
                 ╰────────────────────────────────╯
   label(130)              range (1fr)               output(70)
```

### 2.4 Toggle / int-0..1 — no lane, a pulse

An `i` param with `min0 max1` renders as a **checkbox**; there is no room for a
time strip and a waveform would be absurd at that size. A square LFO on such a
param is *gating*. Represent it as a **single pulsing dot** beside the box,
blinking at the LFO rate (same CSS-animation-seeded mechanism, one element):

```
 ☑ mute-bus   ◉      ◉ pulses in phase with the square LFO
                     (opacity keyframe; NO waveform, NO lane)
```

A fade/loop on a 0..1 int is degenerate (it either sits or steps once) — show
the pulse only for periodic generators; otherwise a static "auto" dot.

### 2.5 Numeric-only `<output>` and the readout question

For a bare numeric readout, the lane is a small strip next to the value. But
the *number itself* must **not** tick every frame — that is precisely the
per-frame full-DOM churn the culture rejects, and a blur of digits is unreadable
anyway. Options, best first:

1. **Show the destination, not the instantaneous value** (fades/loops have a
   known target; show `→ 0.80`). The lane shows motion; the number shows intent.
2. If a live number is wanted, tick it from **one shared 4 Hz `setInterval`**
   that iterates only the *visible, automated* outputs — bounded, coarse, and
   off the animation path. Never rAF, never all rows.

I recommend (1) as default, (2) behind a preference. Either way the digit is
never the animation.

---

## 3. Per-surface treatment table

| Surface (file) | Control | Lane placement | Playhead motion | Numeric readout | Notes |
|---|---|---|---|---|---|
| Live cards — slider (`facilitator.js paramControl`) | range + output | track underlay, spans the `1fr` range column | CSS-seeded, GPU transform | show target `→x` (default) | thumb = value; lane = shape/phase |
| Live cards — toggle | checkbox | none | pulse dot beside box (periodic only) | — | square-LFO gating = blink |
| Live cards — text (`type:"s"`) | text input | **never** | — | — | strings are not automatable (§3.2) |
| All / Group aggregate rows (`liveCard`, `aggregateValue`) | any | lane only if **all members share one generator + phase** | shared playhead only then | — | else → "mixed automation" chip (§5) |
| Seats live tab | same as live cards | same | same | same | identical vocabulary |
| Seat detail / editor sliders (`dashboard.js ~659`) | range | track underlay | same | target | editor is authoring; lane is preview of the sent generator |
| Show tab message inspector (`show.js`) | builder preview | a **static** lane (one full period / whole fade), no live playhead — or a slow demo sweep | optional demo sweep | wire preview already exists | preview = "what this message will do", decoupled from any device clock |

Show-tab preview is deliberately **static or slow-demo**: it visualises the
*message being authored*, which is not yet running on any device, so there is no
real clock to anchor to. A single non-looping demo sweep on hover is enough.

---

## 4. Motion & interaction spec

### 4.1 Seeding (the whole trick)

On generator change or clock resync, JS runs **once** per affected lane:

- **Periodic (LFO, loop)** — set a CSS keyframe sweep:
  `animation: lane-sweep var(--period) linear infinite;`
  `animation-delay: calc(-1 * var(--phase-offset));`
  The negative delay places the animation mid-cycle so it starts **already in
  phase** with `((t_synced/period)+phase) mod 1`. The compositor loops it
  forever with **zero JS thereafter**, and it stays fleet-phase-accurate because
  the seed came from the synced clock. `free` LFOs just seed from a random
  offset instead — same mechanism.
- **Finite (fade, multi-fade)** — a single non-repeating keyframe of duration
  `remaining_ms`, seeded with negative delay for the already-elapsed portion.
  On `animationend`, JS removes the lane (fade retired → plain control).
- **Stop** — no animation; static line + amber tint.

Phase-accuracy vs cheapness is therefore **not a tradeoff here** — the CSS
negative-delay seed is *both* the cheapest option (no per-frame JS) *and* the
phase-accurate one. The only residual JS is re-seeding on resync, which is rare
and event-driven. rAF is not used at all for the playhead. (If a future kind
genuinely needs sample-accurate per-frame drawing — e.g. an approved sh/drift
*history* trace — that, and only that, gets a single shared canvas throttled to
~10 fps; see §7.)

### 4.2 Rate is self-throttling (motion-safety by construction)

The playhead's visual speed equals the generator's real speed. A 20-minute fade
crawls; a 2 Hz LFO wiggles. There is no arbitrary "animation" pouring motion
into the operator's eye — the motion *is* the data, and slow automation is
visually calm automation. This is the dataviz argument that also satisfies the
distraction budget.

### 4.3 Take-over fade-out (the headline interaction)

Touching an automated control sends a plain value and kills the generator. The
animation must **die under the finger** — that dying *is* the feedback.

```
 t=0     pointerdown on the range/thumb
         → add class .taking-over to the lane
         → animation-play-state: paused    (playhead FREEZES where it is)
         → opacity: 1 → 0 over ~160–200ms  (shape + playhead dissolve together)
 t≈180   animationend/transitionend → remove lane node entirely
         → control is now a plain slider at the value you set
```

Freeze-then-fade (not fade-while-moving) is deliberate: the freeze is the
semantic event ("I just seized this"), the fade is the graceful exit. It reads
as "the automation let go the instant you grabbed it." Under
`prefers-reduced-motion`, skip the fade — remove the lane instantly on
pointerdown. The gesture must never make the slider harder to grab: the lane is
`pointer-events: none` throughout, so it can never eat the drag.

### 4.4 Contrast & tokens (theme-safe)

- Shape stroke: `color-mix(in srgb, var(--dim) 55%, transparent)` — recedes on
  `--panel`, still visible in daylight.
- Playhead: `var(--green)` + `filter: drop-shadow(0 0 3px var(--green))`.
- Stop / paused: `var(--amber)`.
- **Never hardcode black-background assumptions.** Express everything through
  the tokens and `currentColor` so the anticipated light/dark toggle flips for
  free. The lane inherits the control's text colour as its baseline.

---

## 5. Edge states

### 5.1 Mixed aggregate (different generators across member Seats)

A single playhead is a **truth-claim about a single phase**. If members run
different generators (or the same generator at different phases), one playhead
would lie. So:

> **Render a moving playhead only when every member shares one generator AND
> one phase. Otherwise render a static "mixed automation" chip — no motion.**

```
 all shared LFO  →   ░╱╲╱╲╱╲░ ●        (one lane, one playhead)
 mixed           →   [ ⧉ auto · mixed ]   dashed baseline, no motion, no value
```

This dovetails with the existing `.mixed` affordance (`aggregateValue`,
placeholder "mixed", indeterminate checkbox): mixed *automation* is the same
honesty as mixed *value* — refuse to fake a single answer.

### 5.2 Offline / unbound

Stored full-state value is a **catch-up constant, not a live frame** (§3.2,
ground-truth). An offline automated param must therefore **not animate** — a
moving playhead on a dead device is a lie about liveness.

```
 offline  →   ~‧‧‧‧‧‧  auto (offline)     ghosted shape @ ~0.3, playhead
                                          FROZEN, tied to the existing offline
                                          dot / .offline dimming
```

The lane goes dim and static; on reconnection it re-seeds from the fresh clock
and resumes.

### 5.3 Muted

Mute is an **output** concern, not an automation-state concern — the generator
keeps evolving under mute. So the lane **keeps animating** (freezing it would
misreport that automation stopped). Signal "you won't hear this" by
**desaturating the playhead** (drop the green glow, mute toward `--dim`) while
motion continues. The lane lives in the value slot and never collides with the
separate `.device-mute-indicator`; the two are orthogonal and both visible.

### 5.4 Stop

Covered in §2.2: flat line, amber tint, `⏸`, no motion. Distinct from constant
(no lane) because "deliberately frozen mid-automation" is worth showing; a
plain constant is not.

---

## 6. What I deliberately do NOT draw

- **No fabricated stochastic future** for `sh`/`drift` — future is dashed
  "unknown", never a plausible fake trace.
- **No per-frame numeric readout tick** — the digit is target-value or a coarse
  4 Hz shared interval, never rAF, never all rows.
- **No scrolling oscilloscope / sample-history buffer** — the shape is known
  analytically; we draw it, we don't accumulate it.
- **No lane on constant/plain controls** — that's just a normal control.
- **No moving playhead on mixed aggregates or offline devices** — motion is a
  liveness/phase claim; don't make it when it isn't true.
- **No axes, gridlines, amplitude labels, or lane border** — it's an ambient
  glyph, not a chart. Chart furniture at 10–14px is illegible noise.
- **No per-shape rainbow** — one ambient stroke colour + one accent playhead.
  Shape identity comes from geometry and linejoin, not hue (also colour-blind
  safe, also fewer tokens to maintain across the theme flip).
- **No waveform inside a checkbox** — periodic int-0..1 gets a pulse dot.
- **No canvas** in the default design (the CSS-transform playhead beats it on a
  tablet). Canvas is reserved solely as the §7 escape hatch.
- **No animation during take-over** — freeze, then fade.
- **No tween on the loop snap-back** — it's an instant jump, per the contract.

---

## 7. Risks & open questions

1. **How many lanes animate at once?** On the Seats tab with N seats × M
   promoted params, dozens of CSS animations could be live. GPU-composited
   transforms scale far better than canvas, but each promoted lane is a
   compositor layer. Mitigation: only lanes **in the viewport** get seeded
   (IntersectionObserver); off-screen lanes are static shape only. Needs a perf
   pass on the cheapest target tablet — this is the constraint most likely to
   bite, and it's a11y/ops' domain to confirm the ceiling.
2. **sh/drift "recent history".** My default draws no history (future unknown,
   past schematic). Bob may want to *see* the last few held values. That is the
   **only** feature that would justify a canvas (one shared, ~10 fps, past
   samples only). I recommend shipping without it and treating it as a gated
   follow-up, because it reintroduces the per-frame cost we just eliminated.
3. **Clock resync churn.** Every resync re-seeds every visible lane. If the sync
   plane jitters, that's a burst of JS. Debounce re-seeds; only re-seed when the
   phase error exceeds a threshold (a few ms of drift is invisible on a 14px
   strip anyway — cheapness and honesty agree again).
4. **Slider thumb vs lane double-encoding.** On a slider both the thumb (value)
   and the lane (shape+phase) are present. Is that redundant or complementary?
   I argue complementary (value-now vs what's-coming), but it's worth a
   real-device look; the instrument-interaction lens may weigh the thumb
   differently.
5. **Show-tab preview clock.** The authored message has no device clock. A
   static/slow-demo lane is my call; if the builder wants a scrubbable preview
   that's a small extra, but it must not imply a live device.
6. **Curve `c:<n>` legibility.** At 10px a bent ramp vs a straight one is a few
   pixels' difference. Worth showing on the roomy live cards; may be
   imperceptible in Ableton-density rows and can degrade to a straight segment
   there without dishonesty (the curve is a nuance, not a state).

---

## 8. One-line summary

Render automation as one reusable **automation lane** — a static SVG shape drawn
once plus a single clock-seeded, GPU-composited CSS playhead (zero per-frame JS)
— honest per generator kind (deterministic futures drawn, stochastic futures
dashed-unknown), silent on constants, motionless on mixed/offline, and dying
under the finger via freeze-then-fade on take-over.
