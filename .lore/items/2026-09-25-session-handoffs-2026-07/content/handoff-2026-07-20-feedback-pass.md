# Handoff — 2026-07-20 (feedback-pass autopilot, second session of the day)

## State of play

Bob's 2026-07-20 morning feedback is laid out on the loom and mostly
worked. The new `17-automation-polish` thread is **fully tied** (goal
included): the fade-builder overlap and the single-segment fade
"release tail" are fixed, the LFO value marker's invalid-custom-property
bug (the "rapid half-waveform dot") is root-caused and fixed, fades now
move the real slider thumb via a DOM-derived rAF animator with an
honest bridge-recorded origin, the ratified marker treatment is amended
(single Opus design pass, per Bob's ruling) to a 12×34 highlight band
behind the thumb, and the loop-forever checkbox is retired in favour of
the Play-again then-action with legacy shows still loading. The
`16-param-automation` goal stitch was tied off (all children were
already tied). `dashboard-theme-toggle` is decomposed into
theme-0 (holistic bop palette — IN FLIGHT, see below) and theme-1
(surfaces + light/dark toggle — not started).

## Tied this session (chronological, with commits)

- Loom layout + `16-param-automation` goal tie — `b19d65c`
- `ap-1-fade-inspector-layout` — `8884c69` (container query; the
  desktop inspector is a fixed 300px column, the old 760px viewport
  media query never fired there)
- `ap-2-fade-preview-tail` — `cdac095` (`shapeFraction` saw wrap at
  phase 1; fixed at both one-shot call sites: Show preview + facilitator
  loop easing; negative test proves the suite bites)
- `ap-4-loop-forever-review` — `bcb8561` (analysis + removal;
  play_count null stays legal; "∞ (legacy)" placeholder)
- `ap-3-slider-automation-visibility` + thread goal — `fbea2b0`
  (marker `slice(2)` fix, fade animator [codex], highlight band
  [design.md, Opus pass], bridge `from` capture)

## In flight / next

- `theme-0-bop-palette-repass` — **TIED** (`f875f46`): Q1 cyan
  sliders/cream toggles, Q2 cyan-soft readouts, Q4 pill-0 nudge,
  eyebrows de-greened; 14-check verify green; review screenshots in the
  tied stitch.
- `theme-1-surfaces-and-toggle` — not started; instructions complete;
  should follow theme-0 directly.
- `dashboard-loading-spinner` — untouched this session; do after
  theme-1 so the spinner uses the final tokens.
- Then `live-param-catchup`, `notify-patch-lifecycle`, stage-12 docs
  close-out (host loom).

## Decisions awaiting Bob (veto-in-review points)

- ap-3 band size/shape: `.loom/tied/ap-3-slider-automation-visibility/band-live.png`
  (screenshot predates the palette repass, sliders still green there).
- Fade `<output>` cosmetic wart: alternates between "→ target" and the
  live numeric between re-renders during a fade.
- theme-0 deliberately did NOT touch the Okabe-Ito group swatches or
  Show pills 1–7 (colour-blind-safe categorical sets). If "think
  groups" meant those four swatches too, that's a Bob decision — flag
  raised here rather than freehanded.

## Gotchas discovered (all healed or recorded)

- Playwright: per-element `scrollIntoView` before `bounding_box()`
  makes rects incomparable — gather all rects in one `page.evaluate`.
- Switching the Show generator `<select>` write-through-persists args
  onto the focused message; use per-kind fixture messages in verifies.
- The bridge stores a fade's destination as the durable seat value at
  send time; anything needing the origin must read the automation
  entry's `from` (added this session, runtime-only).

## Usage at stop (2026-07-20, ~08:00Z)

- weekly (Fable): 96% — resets 2026-07-20T09:00Z (~1h away; next
  session gets a fresh week)
- weekly (all models): 66% — resets 2026-07-20T09:00Z
- 5-hour session: 68% — resets 2026-07-20T05:00Z window
- codex 1-week: 59% — resets 2026-07-25T03:40Z (Bob's ruling this
  session: codex may run to 85%)
