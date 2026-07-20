# theme-1-surfaces-and-toggle — light theme + persistent toggle

The original thread scope (see parent `instructions.md`), landed after
theme-0 so the light theme inherits the holistic bop accent tokens.

## Do

- Tokenise the remaining hardcoded surface colours (`#101316`,
  `#191e23`, `#10161b` inputs, `#14191d` header/rows, etc.) in both
  stylesheets so light is a token swap, not a rewrite. Surfaces may take
  cues from the bop screenshot's lavender panels where it works in dark;
  the light theme should read as the same instrument in daylight.
- Persistent toggle (localStorage; default: follow system) in the header
  of both `index.html` and `facilitator.html`; stamps `data-theme` on
  the root per the ratified pattern (`@media (prefers-color-scheme)` +
  `:root[data-theme=...]` overrides, both directions).
- Update `<meta name="theme-color">` per theme; drop the
  `color-scheme: dark only` pin.
- Contrast-check both themes (4.5:1 text, 3:1 marks), including the
  spatial view, Show tab pills, and the automation markers/bar from
  ap-3. Finalise the provisional light accent values from theme-0
  against the real light surfaces (proposal Q6).

## Verify

House Playwright verify: toggle flips `data-theme` and restyles (sample
a surface + an accent computed style in both states), persists across
reload, system-preference default respected (emulate media), works on
both pages, no console errors. Screenshots dark + light of the main tabs
for Bob.
