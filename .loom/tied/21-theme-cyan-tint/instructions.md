# 21-theme-cyan-tint

**Bob, 2026-07-21:** "The green tint that is throughout the website on the light
theme, for example on the named steps, I'd like to shift that a bit towards cyan,
so really it's more purple and cyan than it is purple and green."

Authorized by lore item `2026-07-21-show-console-dock-and-fixes-braindump`.

This is a palette repass, not a redesign — the successor to
`theme-0-bop-palette-repass` (tied; read its artifacts first, the reasoning for
the current values lives there).

## Outcome

- The light theme's green-leaning accent shifts toward cyan. The palette reads
  purple-and-cyan.
- Do it **at the token layer**: `dashboard/static/css/style.css` already carries
  `--green`, `--accent`, `--accent-bright`, `--accent-cyan`, `--accent-cyan-soft`,
  `--accent-soft`, `--accent-warm`. Retune the tokens; do not sprinkle new hex
  values at call sites. If the right answer is that `--green` should stop
  existing as a hue and become a semantic token, say so and do it.
- Named steps in the Show tab are Bob's cited example — check them explicitly,
  but the sweep is app-wide across the light theme.
- **Dark theme is not in scope** unless the same token drives both; if it does,
  check dark hasn't regressed and say so.
- Semantic colours that must stay distinguishable keep their meaning: success/
  online green vs the accent cyan must not converge into one indistinguishable
  hue. Enumerate the semantic uses before retuning.
- Contrast: keep text/background pairs at or above their current WCAG ratio.
  Record before/after ratios for the pairs you touch.

## Verify

Screenshots of each tab in the light theme before and after, side by side, for
Bob. Contrast ratios recorded in the stitch. Existing tied Playwright suites
re-run unmodified — a token change should break none of them; if one breaks, it
was asserting on a colour and that is worth knowing.
