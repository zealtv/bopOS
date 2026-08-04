# Decisions

- The active Control layout now resets direct cards to
  `flex: 1 1 min(340px, 100%)`. This deliberately matches the old ID selector's
  specificity and appears later, allowing the shared `.target-card` 560px cap
  to remain the component-owned ceiling.
- Kept the legacy compact declaration in place because it is embedded in a
  large historical one-line block; the active layout boundary already
  supersedes the rest of that retired horizontal-row rule. The living static
  test inspects the final direct-child block so a future cascade regression is
  caught.
- The browser journey now checks growth, not merely equality and bounds: four
  Control cards at 1800px must each exceed 400px.
