# Global menubar UI/UX review

Reviewed against Bob's four 2026-07-20 screenshots and the current Dashboard
HTML/CSS before implementation.

## Recommendation applied

Organize the bar as:

> identity → mode switch → health → emergency control → appearance

- Remove the visible `execution target` label and duplicated current-mode text.
  The segmented control already communicates the state; retain
  `role="group" aria-label="Execution target"` and its `aria-pressed` buttons.
- Keep the full **Live Fleet / Simulation / Patch Edit** labels.
- Treat online count and connection as one health cluster. Connection is
  secondary; **MUTE ALL** remains the strongest operational action.
- Replace the flat universal gap with cluster-level spacing and align controls
  around a common 38–40 px desktop height.
- Keep the tab row visually separate because it is navigation rather than
  global system state.
- Below desktop width, use a deliberate second row for the full-width mode
  switch. At phone width each mode receives one third of the available width,
  while connection and MUTE remain visible.

The implementation follows this hierarchy and was checked at 1280, 900, and
420 CSS pixels.
