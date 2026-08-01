# 3-tokens-and-chrome

First implementation slice of the ratified control-panel design (design and
authority: `control-panel-design.md` + `design-language.md` + the reviewed
`mockup-control-panel.html` in the tied `2-control-panel-design` stitch).

Land the new token layer and chrome, **no DOM changes**:

- Add `--mod`, `--mod-fill`, `--mod-hatch`, `--mod-soft`, `--value-fill`,
  `--hatch`, `--radius-momentary` (7px), `--radius-toggle` (1px) to
  `dashboard/static/css/style.css`, dark + light values per the
  design-language token table.
- Light-theme base repaint (saturated pink pastel family) scoped to the
  control surface only — the app-wide repaint belongs to
  `02-app-wide-rollout-design`.
- Focus policy: `accent-color: var(--accent)` and a purple
  `:focus-visible` outline on the control surface; no user-agent colors.
- Button shapes: momentary rounded 7px; latching sharp via
  `button[aria-pressed]`; ∿ icon circular.

Constraint: the surface keeps working throughout (evolve `ControlSurface`,
don't fork). Verify: `tools/run-tests.sh browser` green; before/after
screenshots of the Control tab and Device-tab panel into this stitch.
