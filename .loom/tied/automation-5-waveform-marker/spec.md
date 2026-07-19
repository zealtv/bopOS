# automation-5 spec — Slices 2+3 of the ratified waveform treatment

Authority: `.loom/tied/automation-4-waveform-ux-gate/judgment.md` §3
(Layers 2–3, per-control table, take-over, reduced-motion, ARIA), §5
Slices 2–3, §6 verification sketch. `ratification.md` beside it records the
muted-device default (marker keeps moving, desaturated). Slice 1 landed in
`.loom/tied/automation-3-animated-takeover/` (see its notes.md/spec.md):
`installation.automation[seat][identity]` = `{args, kind, shape, free,
sent_at}`, glyphs/aria/mixed/offline/take-over drain already exist in
`facilitator.js`, and `window.ParamSpec.parse` is the shared parser.

Build exactly the judgment's Slice 2 and Slice 3:

**Slice 2 (facilitator.js + facilitator.css/style.css):**
- Paint-once `--auto` track state on automated sliders (solid 2px inset
  bar/tint, no alpha wash).
- In-flight fade = CSS width-grow toward the target (reuse the
  `show-step-progress` mechanism; seed duration/progress from `sent_at` +
  fade segments; on completion the control is a constant — treatment
  clears; no per-frame JS).
- Value-axis overlay marker (`pointer-events:none`, absolute over the range
  track, CSS `transform` keyframes) for `sine/tri/saw/square` LFOs and
  `loop`: per-shape `@keyframes`, min/max mapped via custom properties,
  `animation-duration: var(--auto-period)`, phase anchor
  `animation-delay: calc(-1 * var(--auto-elapsed))` computed from `sent_at`,
  §3.2 clock phase, and the `p:` option in the tracked args. Loop snaps at
  the seam. `sh`/`drift`: no marker (glyph only). `free`: hollow marker,
  local arbitrary phase. Muted device: marker continues, desaturated toward
  `--dim`.
- Take-over freeze-then-drain: `animation-play-state: paused` on
  pointerdown, then the existing drain; extend the `interacting` guard gap
  for checkboxes as ruled. Reduced-motion: one media block kills all marker
  animation (static layer already carries the state).
- Re-anchor `--auto-elapsed` only on real `state` broadcasts and only when
  phase error is meaningful (debounce; no timers of its own).

**Slice 3:**
- Automated numeric `<output>`s show the fade target while in flight or the
  static catch-up value + kind otherwise — no per-frame digits, no rAF, no
  intervals.
- Show message inspector (in `show.js` beside `renderParamBuilder`): one
  static SVG preview of the generator being authored — ≤2 cycles, value on
  y / time on x, redrawn only on edit, no clock anchor, at most one on
  screen; honest omission for `sh`/`drift` (label "random — not previewable"
  or similar); nothing rendered for value/stop/raw-fallback modes.

Files you may touch: `dashboard/static/js/facilitator.js`,
`dashboard/static/js/show.js`, `dashboard/static/js/paramspec.js` (shared
helpers like phase/period extraction belong here),
`dashboard/static/css/style.css`, `dashboard/static/css/facilitator.css`,
and the new verifier
`.loom/threads/16-param-automation/automation-5-waveform-marker.stitching/verify_waveform_marker.py`.
No Python changes, no `.loom` claims/ties, no commits.

**Verifier** (house pattern; copy the harness from
`.loom/tied/automation-3-animated-takeover/verify_automation_takeover.py`,
including the datagram proxy and the `#ws-status` `state="attached"` wait):
1. Sine LFO on a seat → marker element exists, computed
   `animationName`/`animationDuration` match shape/period, and
   `animationDelay` is negative (phase-anchored).
2. `sh` generator → glyph but no marker element.
3. In-flight fade → progress mechanism present with finite duration; after
   completion (short fade) treatment clears to plain.
4. Zero-OSC while animating (proxy sees no extra `/p/` traffic).
5. Take-over pauses then clears (one plain datagram — reuse the a3 check).
6. Reduced-motion emulation → no running marker animation, glyph intact.
7. Show inspector: author an LFO message → one static `<svg>` preview,
   focusing/re-rendering does not rewrite the message args (reload +
   compare persisted show file); `sh` shows the honest no-preview label.
8. No console errors.
Sandbox cannot bind sockets — write it, state you could not run it.

Acceptance checks (orchestrator runs): the three `node --check`s, this
verifier, then the tied a3 verifier, tied a2 builder suite, and engine
parity; `git diff --check`.

When done, summarize what you changed, how you verified what you could, and
anything you could not do. If you could not complete the task, say so
explicitly.
