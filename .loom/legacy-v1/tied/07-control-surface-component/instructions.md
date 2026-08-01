# 07-control-surface-component

Extract the live control surface into one reusable component so the Device tab
(09), the Control tab (10), and the generator drawer (08) all render the same
thing.

**Authority:** `.loom/tied/5-live-control-placement-design/decisions.md` (Bob,
2026-07-25) — "yes — same component, different send."

## Where the code actually is (surveyed 2026-07-25)

The live surface is **not** in `dashboard.js`. It lives in
`dashboard/static/js/facilitator.js`, rendered by `dashboard/static/facilitator.html`,
which the Dashboard tab embeds through an **iframe**
(`index.html:22`, `src="/facilitator?embedded=1"`).

The pieces to extract:

- `paramControl(scope, id, members, declaration, disabled)` — one row: string /
  boolean / numeric-with-range, mixed state, automation glyph + marker + fade
  attrs, precision-field readout.
- `paramTree(scope, id, members, declarations, disabled)` — nested path grouping.
- the `[data-live-param]` binding half of `bindCards()` — takeover, throttled
  send, `PrecisionField.attach`, checkbox/indeterminate handling.
- the supporting fade animator (`animateFades`/`startFadeAnimator`/`finishFade`)
  and the automation model helpers (`automationModel`, `automationPresentation`,
  `automationForSeat`, `aggregateValue`, `refreshAutomationAnchors`).

`dashboard.js` has a *second*, simpler renderer for the patch editor
(`editorControl` / `editorParamTree`, ~line 696). Do **not** try to unify it in
this stitch — the editor writes manifest declarations, not live values. Note the
overlap and move on; the editor is a later candidate host, not this bite.

## What to build

`dashboard/static/js/control-surface.js` exposing `window.ControlSurface` with a
render + bind pair, taking an explicit **context** object rather than reaching for
module-level state. The entangled globals it currently closes over are
`installation`, `automationAnchors`, `takeoverAnnouncements`, `interacting`, and
`deviceForSeat` — pass them in (or expose them via the context) so the same code
runs on both pages.

The component's inputs are exactly:

- **`scope`** — `all` | `group` | `seat` | `device` (device is new; 09 uses it)
- **`id`** — group/seat id, or uid for device scope
- **`members`** — the seats whose values are aggregated
- **`declarations`** — the promoted schema to render
- **`disabled`** — render disabled (offline devices, per 09)
- a **send** callback, so the host decides the wire message

## Constraints

- **No user-visible change in this stitch.** `/facilitator` and the embedded
  Dashboard tab must render and behave byte-for-byte as before. This is a pure
  extraction; anything that looks like an improvement belongs to 08/09/10.
- Both `facilitator.html` and `index.html` must load the new script (index.html
  needs it for 09).
- Mixed-aggregate behaviour is *carried over unchanged* — 08 explicitly reuses it
  rather than branching on generator mode.

## Verification

Durable tests go in `tests/`, not a new tied guard (thread-27 policy). The
existing live-control Playwright coverage is the regression net for "nothing
changed" — find it, run it, and add a `tests/` check that the extracted
component renders identically for `all` / `group` / `seat`.
