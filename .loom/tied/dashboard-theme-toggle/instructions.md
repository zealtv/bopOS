# dashboard-theme-toggle

A light/dark mode toggle for the dashboard (and facilitator page). The rig
sees daytime use; operators need a legible light theme without losing the
dark performance look.

Groundwork already in place:

- The ratified automation treatment (`.loom/tied/automation-4-waveform-ux-gate/judgment.md`,
  "Theme portability") established the pattern: every accent is a token pair
  driven by `@media (prefers-color-scheme)` **plus** `:root[data-theme=...]`
  overrides, so an explicit toggle stamps `data-theme` on the root and wins
  in both directions. `--auto` already ships that way.
- The `dashboard-bop-accents` thread proposes the accent tokens as
  dark/light pairs; land it first (or together) so the light theme inherits
  the bop accent language rather than re-deriving it.

**2026-07-20 (Bob):** the bop-accents repass is folded INTO this thread —
the site still reads green; he wants the full `bop.casio~` palette
holistically (groups, sliders, highlights), tackled together with the
toggle. Decomposed: `theme-0-bop-palette-repass` (holistic colour pass,
resolves the tied proposal's §6 questions — Q1 answered yes) then
`theme-1-surfaces-and-toggle` (surface tokens, light theme, the toggle
itself — the original scope below). The reference screenshot
`Screenshot 2026-07-20 at 09.43.48.png` sits in this thread dir; the
other two screenshots here belong to `17-automation-polish` ap-1/ap-2.

Scope (now theme-1):

- Tokenise the remaining hardcoded surface colours (`#101316`, `#191e23`,
  `#10161b` inputs, `#14191d` header/rows, etc.) so a light theme is a token
  swap, not a rewrite.
- A persistent toggle (localStorage; default: follow system) in the header,
  present on both `index.html` and `facilitator.html`; update the
  `<meta name="theme-color">` and drop the `color-scheme: dark only` pin.
- Contrast-check both themes (4.5:1 text, 3:1 marks), including the spatial
  view and Show tab pills.
- House Playwright verify: toggle flips `data-theme`, persists across
  reload, system-preference default respected, no console errors.
