# ap-1-fade-inspector-layout — fade segment row overlaps at narrow widths

**Bug (Bob, 2026-07-20):** in the Show inspector's fade builder, the
DESTINATION and DURATION interface items obscure each other when the
inspector is narrow. Screenshot:
`.loom/threads/dashboard-theme-toggle/Screenshot 2026-07-20 at 09.48.11.png`
— the two field labels render as one run-together string
("DESTINATIONDURATION") and the duration number input collapses to just
the unit select, while the wide layout
(`Screenshot 2026-07-20 at 09.49.29.png`) is fine.

## Do

- Find the fade segment row markup/CSS (built by the generator builder in
  `dashboard/static/js/show.js`; styles in `dashboard/static/css/style.css`).
- Make the segment row wrap gracefully at narrow inspector widths:
  labels stay attached to their own fields, the destination and duration
  inputs never overlap or collapse to zero width, Remove stays reachable.
  Container-width-driven (the inspector column can be narrow even on a
  wide window) — prefer `flex-wrap`/`grid` with sensible `min-width`s
  over a viewport media query.
- Keep the compact Ableton-ish density; don't redesign the builder.

## Verify

House Playwright verify: drive the dashboard at a narrow viewport (and/or
narrow inspector), add a fade segment, and assert via bounding boxes that
the destination and duration inputs and their labels do not overlap and
each input has usable width (> ~40px). Screenshot narrow + wide for the
stitch.
