# automation-5 notes — 2026-07-20

Slices 2+3 of the ratified treatment
(`.loom/tied/automation-4-waveform-ux-gate/judgment.md`). Implementation
delegated to GPT 5.6 Sol via codex against `spec.md`; review and all
socket-bound verification by the orchestrator.

## What landed

- Facilitator sliders: paint-once `--auto` track state; in-flight fades as
  finite CSS width-progress seeded from `sent_at`; value-axis overlay
  markers (pure CSS keyframes per shape, `pointer-events:none`, negative
  `animation-delay` phase anchor from the tracked args and clock) for
  sine/tri/saw/square/loop; `sh`/`drift` glyph-only; `free` hollow marker;
  muted desaturation; take-over pauses then drains; reduced-motion kills
  all marker animation; checkbox `interacting` gap closed.
- Numeric outputs show fade target in flight or catch-up value + kind.
- Show inspector: one static SVG generator preview (≤2 cycles, redraw on
  edit only, no clock anchor), honest no-preview label for `sh`/`drift`.
- Shared phase/period/waveform helpers in `paramspec.js`.

## Verification (orchestrator, 2026-07-20)

- `verify_waveform_marker.py` (this dir) — 17/17 PASS (real server +
  simfleet + datagram proxy + headless Chromium; includes zero-OSC,
  reduced-motion, take-over single-datagram, preview round-trip).
- Regressions: tied a3 take-over suite (2× green after a harness heal —
  see below), tied a2 builder suite, automation-1 engine parity — green.
  `node --check` ×3, `git diff --check` — clean.

## Harness heal folded back into the tied a3 verifier

`Locator.scroll_into_view_if_needed` waits for element stability; the new
marker animation keeps the node perpetually "unstable" and heartbeat
re-renders can detach it mid-wait. Both this verifier and the tied
`automation-3` one now use a one-shot JS `scrollIntoView` plus a fresh
bounding box. New house gotcha recorded in CLAUDE.md.
