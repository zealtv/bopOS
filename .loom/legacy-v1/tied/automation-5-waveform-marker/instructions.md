# automation-5-waveform-marker

Implement Slices 2 and 3 of the ratified waveform treatment — the authority
is `.loom/tied/automation-4-waveform-ux-gate/judgment.md` (ratified
2026-07-20 under Bob's pre-ratification; see `ratification.md` beside it).
Do not re-litigate the design.

Requires `automation-3-animated-takeover` (generator tracking state, the
take-over gesture, and the Slice-1 static glyph layer land there).

Scope:

- **Slice 2 — slider motion.** Paint-once `--auto` track state; in-flight
  fades reuse the `show-step-progress` CSS mechanism; the value-axis overlay
  marker (`pointer-events:none`, CSS transform + per-shape `@keyframes`,
  negative `animation-delay` phase anchor from the synced clock) for
  `sine/tri/saw/square/loop`; `sh`/`drift` stay glyph-only; `free` LFOs
  animate shape/rate with the hollow "free" marker; freeze-then-drain
  take-over including the checkbox `interacting` gap; the reduced-motion
  block; bounded re-anchor of `--auto-elapsed` on existing state ticks.
- **Slice 3 — numeric/output polish + Show inspector preview.** `<output>`
  shows fade target or static catch-up value + kind (no per-frame digits);
  the single static SVG generator preview in the Show message inspector
  (≤2 cycles, redrawn on edit only, no clock anchor) — coordinate with the
  landed automation-2 builder rather than duplicating its parse.

Verify: the judgment's §6 sketch — house Playwright pattern asserting glyph
+ aria state, zero-OSC animation, one-plain-value take-over, offline
stillness, honest `auto·mixed`, reduced-motion, and `sh` glyph-only.
