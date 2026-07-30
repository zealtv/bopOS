# 05-value-box-component

One numeric entry primitive, used everywhere.

`design-language.md` §4 names 58px as *the* standard number-box width — "every
numeric entry box (param rows, drawer args, segment `to`/`in`, event values)
unless a box must hold visibly longer values" — and §9 makes click-to-type
precision entry universal. Neither holds today.

`js/precision-field.js` (`PrecisionField.attach`) has **three** call sites
(`control-surface.js:945`, `dashboard.js:1040`, `dashboard.js:1060`). Raw
`type="number"` inputs, none of them precision fields:

    index.html 9 · control-surface.js 1 · dashboard.js 9
    param-generator.js 16 · show.js 12

The 16 in `param-generator.js` are the drawer arg boxes the mockup draws as
value boxes; the 12 in `show.js` are inspector fields.

Work:

- Extract a value-box component: 58px, `--input` face, `--radius-small`,
  tabular numerals, click-to-type precision entry, clamped to min/max, rounded
  to 6 significant figures (PD OSC floats are 32-bit — the house rule).
- **Alignment says the kind**: floats left-align, integers right-align
  (Bob, 2026-07-27).
- Convert every numeric entry in the inventory's count. Where a box genuinely
  needs to be wider, say why in `decisions.md` rather than varying silently.
- Keep the existing decoupling: callers pass a plain spec, so a control shown
  in different units than it sends (the master `%`) drives the field in
  display units and converts inside `commit`.
