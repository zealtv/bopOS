# Make modulation number fields editable by primary click

Fix the Control and Remote hosts' interaction guards so a primary click on a
generator drawer number input does not trigger the document-level pointer-up
redraw and replace the newly focused input.

## Acceptance

- Pointer-gesture state and component/focus interaction state cannot clear one
  another accidentally.
- A primary click leaves a generator number input focused and editable across
  live fleet heartbeats in the desktop Control tab and Remote surface.
- Slider, toggle, enum, fire-feedback, preset-drawer, and precision-input render
  guards retain their current behavior.
- Extend the focused browser regression to exercise a real primary click rather
  than programmatic `focus()`; verify Chromium and Firefox where the installed
  Playwright browsers permit it.

Run the focused interaction-guard journey and the browser tier before tying.
