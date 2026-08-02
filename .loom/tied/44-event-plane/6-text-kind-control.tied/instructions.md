# 6-text-kind-control

A styled control-panel component for the `text` kind. Deferred by Bob,
2026-07-28: "we currently don't have any UI for strings. That can be put off
to later but if strings are in the contract, they should be implemented in the
manifest and given styled control panel components in the future." The
manifest half was not deferred; it landed in child `2`.

Kept in this thread at Bob's instruction rather than moved to
`desktop-ui-overhaul`.

## Status — claimable now, and it is the last one (2026-08-01)

**No longer blocked.** This stitch was ordered behind the app-wide UI work so
it would adopt the shipped text treatment rather than compete with it. That
work is done: `desktop-ui-overhaul` is tied in full, including
`02-component-unification` and its `11-ground-and-card-audit`. The design
language it was told to wait for now exists and is described below.

It is also **the only loose end left in the loom**, and the last thing standing
between thread `44-event-plane` and its tie — `5-pd-adoption` tied 2026-08-01
on Bob's call.

## Actual starting state (re-measured 2026-08-01)

There is an **unstyled** control, not no control:

* `control-surface.js:564` maps a `text` declaration to a `"string"` shape;
* `control-surface.js:633-634` renders a plain `<input type="text">`.

**Correction to this stitch's earlier text, which said strings are "excluded
from aggregation": they are not.** `aggregateValue` (`:80`) is kind-agnostic,
the string row reads `mixed` from it like every other row, and a mixed
aggregate already renders as an empty field with `placeholder="mixed"` and
`data-mixed="true"`. So the open question is not *whether* to aggregate — it is
whether that placeholder is the right treatment, and whether it should carry
the ratified mixed hatch the numeric rows use.

What IS excluded is automation: `numericDeclaration` (`:193`) lists
`float`/`int`/`toggle`/`enum` and omits `text`, so `generatorAvailable` is
false and no ∿ drawer is offered. That is correct and stays — see Scope.

The earlier line citations (282 / 352 / 64 / 101) are stale; `06-control-panel-
reflow-and-editor` moved this file substantially. Re-measure before trusting
any number here, including these.

## What shipped that this must adopt

* **Authority for the row design** is the tied `2-control-panel-design`:
  `control-panel-design.md` §2 kind table and `design-language.md`. Extend the
  kind table with text rather than inventing a parallel treatment. Where prose
  and the living prototype `mockup-control-panel.html` disagree, the prototype
  as last reviewed by Bob wins.
* **The app has five component stylesheets** (`param-generator.css`,
  `value-box.css`, `target-picker.css`, `control-column.css`, plus
  `control-panel.css` itself) and **one** metric layer — `--row-h`,
  `--gap`, `--radius-*`, `--pad-control`, `--pad-panel`, `--header-h`, all at
  `:root` in `control-panel.css`, the one file both documents load. `--chrome-*`
  is gone. Do not introduce a third.
* **`PrecisionField` / `value-box.css` owns the 58px numeric entry face**,
  including spinner suppression. A text field is not a value box, but the box's
  face is the nearest shipped idiom for "typed entry in a control row" — look at
  it before drawing a new one.

## Two guards that will fail you if you write CSS the old way

* **`tests/test_css_component_ownership.py`** (browser-free, in `fast`). If the
  text row's rules are scoped to the surfaces it is mounted in
  (`.live-card`, `.device-control`, `.show-inspector-section`, `#editor-params`)
  rather than to the row's own root, this fails. That guard exists because the
  thread hit the same defect four times; its allowlist is deliberately **empty**.
* **`tests/verify_ground_and_card.py`** (browser). Design-language §12: `--bg`
  is the workspace ground and shows only as gutter. A text input must not be
  painted `var(--bg)` — use `var(--input)`. `11-ground-and-card-audit` found and
  fixed exactly that declaration on `facilitator.css`'s `.live-param
  input[type=text]`, where it had been dead but wrong; do not reintroduce it.

## Scope

- A text row in the control-panel design language (authority above).
- Decide and document the questions the other kinds answered:
  * **commit on blur or on Enter** — `dashboard/static/js/precision-field.js` is
    the nearest shipped idiom;
  * **what "mixed" should look like** across an aggregate target, given the
    placeholder treatment that already exists;
  * whether a **max length** belongs in the manifest.
- Text takes **no generators** — it is not numeric, and §3.2 automation is a
  numeric grammar. Keep it out of the ∿ drawer, as today.

## Verify

Extend the living control-surface journey with a text param — render, edit,
commit to the wire via simfleet, and survive a heartbeat re-render.

That last one is the trap, and it has bitten this surface twice:

* `47-live-param-kinds-flake` — `renderCards()` replaces the live-card DOM
  every heartbeat, so a focused control can be replaced out from under the
  operator mid-edit. A text field being typed into is precisely this hazard.
* `52-preset-drawer-name-discarded` — the guard meant to prevent that had
  **never once run**, because `onfocusin` is not an event-handler IDL attribute
  and the assignment was an inert expando. Use
  `addEventListener("focusin"/"focusout", …)`; `tests/test_dom_event_handlers.py`
  bans the non-IDL names in source, and `tests/verify_interaction_guard.py`
  asserts live that they are still not IDL attributes.

Two Playwright notes from CLAUDE.md that apply directly here: fixture manifests
use explicit `kind`, and a `text` default, **when present, must be a string** —
an invalid default fails with a named manifest error (gotcha 7). And a
`<input type="range">` cannot test whether focus holds the render guard
(gotcha 23) — a text field can, and should.
