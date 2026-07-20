# ap-3 notes

## Part 1 — the marker bug (root cause of everything Bob saw)

`paramControl` built the sine keyframe custom properties with
`String(fraction).slice(1)` → `--auto-p.03806` — a dot in a custom
property name is invalid CSS *and* doesn't match the keyframes'
`var(--auto-p03806)`. Six of the eight sine keyframes therefore resolved
to invalid → `transform: none`: the dot parked at zero for most of the
cycle, then darted to max and back around mid-cycle. Exactly "moving
unexpectedly rapidly… only half of the waveform… like it wasn't zeroed
properly". Fixed with `slice(2)` (probe evidence: `probe_marker.py` —
before: flat zero + one dart; after: clean full-range sinusoid at the
authored 10s period).

## Part 2 — fades move the real slider

Per `spec-fade-animator.md` (implemented by codex, GPT 5.5, reviewed
here): fade metadata is stamped as data attributes on the range input;
one module-level rAF loop re-derives everything from the DOM each frame
(survives heartbeat re-renders), moves the thumb with the shared ramp
math, never dispatches events or sends OSC, skips inputs under a finger,
throttles to ~1Hz under reduced motion, and performs completion cleanup
(it inherited this from the deleted fade-progress `onanimationend`).

Seam found in verification: the bridge stores the fade *destination* as
the durable seat value at send time, so the frontend had no honest
origin — the thumb sat at the target. Fix: `osc_bridge.set_param` now
records `from` (explicit `spec.start`, else the pre-overwrite stored
value) in the runtime automation entry; the frontend prefers
`parsed.from ?? entry.from ?? value`. Runtime-state only — no contract
or wire change; forgotten on restart by design.

## Part 3 — the highlight band (single Opus design pass, per Bob's ruling)

`design.md` is the treatment spec (amendment to the automation-4
judgment, authorized by Bob's 2026-07-20 feedback): the 4×8px dot became
a 12×34px solid `--auto` pill re-layered *behind* the slider thumb
(z-index 1), reusing every existing keyframe and custom property.
Fade progress bar retired (redundant with a moving thumb). Offline and
reduced-motion now *hide* the band (a tall bar frozen at min lies about
the value); muted keeps moving desaturated; take-over pause/drain
unchanged. `sh`/`drift` stay glyph-only.

**For Bob to veto in review:** band size/shape (`band-live.png` — dark
theme, pre-bop-palette so sliders still green there), and the small
cosmetic wart that a fade's `<output>` alternates between "→ target" (at
re-render) and the live numeric (animator frames) until completion.

## Verify

`verify_slider_automation.py` — 13 checks, all PASS (2026-07-20):
10s-sine marker sweeps both extremes at the authored period without
darting; band geometry 12×34 behind the input; fade-progress element
gone; a 30s fade moves the thumb monotonically; a finger freezes the
animator; take-over sends exactly one plain datagram; the animation
emits zero parameter OSC; reduced motion hides the band; no console
errors. Run: `~/.venvs/bopos/bin/python verify_slider_automation.py`.
