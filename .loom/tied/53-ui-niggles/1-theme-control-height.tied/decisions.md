# Decisions

- The theme select now derives its minimum height from `--row-h`, the shared
  control metric, instead of restating the header's 40px height. No mode-group
  or narrow-layout styling changed.
- The living ground-and-card browser journey now measures the header against
  the tallest of the theme select and execution-mode group at 1280px, 900px,
  and 700px in both light and dark themes. This guards the relationship rather
  than a CSS literal.
