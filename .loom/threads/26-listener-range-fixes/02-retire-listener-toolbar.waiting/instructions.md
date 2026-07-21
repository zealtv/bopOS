# 02-retire-listener-toolbar

**Bob, 2026-07-21:** "remove the listener tool bar — not required, all control
can be graphical."

Do this after `01-range-field-rendering-fixes` is tied.

## Remove

- `#listener-bar` in `dashboard/static/index.html:39-43` — the `Listener`
  label, the `range` number input, the `heading` number input, and the
  `#listener-readout` output.
- `bindListenerBar()` and its call site (`spatial.js:~191`, `~261`).
- The toolbar writes inside `paintRange()` (`spatial.js:219-223`) and anywhere
  else that reaches for `listener-range` / `listener-heading` /
  `listener-readout` by id. `grep -rn "listener-range\|listener-heading\|
  listener-readout" dashboard/` and clear every hit, CSS included.
- Any `.waiting`-free leftovers: the row's layout rules in `style.css`, and the
  "Add Point / No points" row's spacing once its right-hand neighbour is gone —
  make sure that row still reads correctly on its own at narrow widths.

## Keep working

Everything the toolbar did must remain reachable graphically — this is the
whole basis of Bob's ruling:

- heading — drag the tip handle (`.listener-tip` / `.listener-tip-hit`).
- range — collar drag, wheel over the puck, and the keyboard range keys.
- position — puck drag and arrow keys.

Do not regress accessibility: the puck's `aria-label` currently carries heading
and range (`spatial.js:164-165`), and with the numeric fields gone it becomes
the only textual statement of those values. Make sure it updates live from
`paintRange()` / `paintHeading()` rather than only at render, and confirm the
keyboard paths still work with no visible focusable input in the row.

Consider — and decide explicitly in `decisions.md` — whether a transient
on-canvas readout near the puck (during drag only) replaces the retired
`#listener-readout`. Bob said all control can be graphical; he did not say
values must be invisible. Recommend, don't over-build; if it is more than a
small label, propose rather than implement.

## Verify

- Playwright verify in this stitch directory: `#listener-bar` absent; heading,
  range, and position all still settable by pointer; keyboard range/heading
  steps still work; `aria-label` reflects live values mid-gesture; the values
  round-trip to the server (`set_listener`) and survive a reload.
- Screenshot of the tidied Seats header row, dark and light, at wide and narrow
  widths.
- Re-run the tied `22-listener-range-ux` guards. Any that drive the numeric
  fields are **superseded by this stitch** — repair them to drive the graphical
  gesture instead, with an inline comment naming this stitch, and record it in
  `decisions.md`.
