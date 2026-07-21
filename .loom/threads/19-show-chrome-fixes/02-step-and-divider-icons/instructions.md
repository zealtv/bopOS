# 02-step-and-divider-icons

**Defect (Bob, 2026-07-21):** "In the toolbar, when it's narrow, the divider
button is a minus and the step button is a plus, and that is confusing
iconography because it seems like it's add step and remove step. I think we
need better icons for step and divider."

Both buttons *add* — `add-step` and `add-divider` (see `editBarButton` calls in
`dashboard/static/js/show.js`, around the `add-divider` / `add-step` actions).
At narrow widths the labels drop and only the glyphs remain, so `+` / `—` read
as add/remove.

## Outcome

- Two glyphs that read as "add a step" and "add a section divider" without
  labels, and that do not read as an opposed pair.
- Whatever the glyphs, the *additive* sense must survive label-less rendering —
  if that means both carry a small `+`, or both drop to labelled buttons at
  narrow widths, that is an acceptable answer; state the reasoning in the
  stitch.
- Keep the existing accessible names (`aria-label` / `title`) — they are the
  screen-reader contract and the Playwright selectors.
- Consistent with the rest of the app's glyph vocabulary (⋮⋮ grab handle, the
  eye/eye-off pattern). Do not introduce an icon font or external asset — the
  app is self-contained.

## Verify

Visual check at narrow and wide widths plus a Playwright assertion that both
buttons still resolve by their accessible names and still add the right item
kind.
