# 08-control-tab-columns

**Un-waited 2026-07-30: Bob answered the gate questions.** Still needs
`07-target-selector-component` to exist first — that is an ordering
dependency, not a blocker on a decision.

Bob, 2026-07-30: the control panel *"works really well when it's a relatively
narrow column"*, so the Control tab should host N columns rather than one
panel — each column a control panel with its own pop-out target selector, each
targeting all / a selection of groups / a selection of seats / a mixture.
Simple add and remove, **minimum one**, so the tab is never empty. The
All/Groups/Seat radio row at the top goes away.

Today the Control tab is a heading, a link, and one iframe
(`index.html:25-28`, `#dashboard-live-view` → `/facilitator?embedded=1`), with
the target radios living inside the iframe.

## Ruled by Bob, 2026-07-30

- **RETIRE THE CONTROL-TAB IFRAME.** `ControlSurface` is hosted directly in the
  parent document; `/facilitator` becomes the standalone **Remote** view only.
  This removes the cross-document coordination that `control-panel.css`'s
  header and CLAUDE.md Playwright gotcha 15 both exist because of. Expect to
  touch: `index.html:27` (`#dashboard-live-view`), `facilitator.js`'s split
  between page bootstrap and surface hosting, and every test that reaches the
  Control surface through `page.frame_locator("#dashboard-live-view")`.
  Gotcha 15 should be *deleted* from CLAUDE.md once it stops being true.
- **Column layout persists in `localStorage`** — consistent with
  `bopos.control.collapsed-branches` and `bopos.device-control-open`. Bob:
  *"with a chip picker it should be easy to spin up whatever control panel
  targets one needs"* — cheap re-creation is the argument against needing
  durable server-side layout.

## Still to settle in the proposal
- How a column's target interacts with the applied-preset marker and its
  derived dirtiness (`41-preset-primitive` R5).
- Column widths: fixed at the panel's minimum, or resizable.
- What happens to the per-column panel when its target resolves to no seats.

Deliver a written proposal plus mockups at 1280/1680/2560. Do not implement
past ratification.

## Added 2026-07-30 (Bob's tab-by-tab review) — ground and card

Retiring `#dashboard-live-view` also retires the app's clearest
design-language **§12** violation: that iframe sets `background:var(--bg)` and a
border, so the Control tab shows a bordered pink box with the panel swimming in
it (Bob's words: *"swimming in empty space"*).

§12: `--bg` is the workspace ground, visible only as gutter *between* cards, and
nothing but the page may set it. So when this stitch lays out N columns, the
columns are cards on the ground — the ground shows as the gap between them, and
never inside a column's footprint. Delete the `background:var(--bg)` declaration
with the iframe rather than porting it to the column container.
