# 2-control-column-component

Extract a `ControlColumn` component from `facilitator.js` — **instance state,
no module globals** — so that N of them can exist. Keep it inside the iframe.
No design gate; this is a refactor.

**Deliberately no visible change.** The four existing journeys keep reaching
through `page.frame_locator("#dashboard-live-view")` and keep passing,
untouched. That is the point of doing this before `3`: it puts the risky
extraction behind an unchanged document boundary, so a break is attributable to
the extraction rather than to the document move.

## The problem

`facilitator.js` is 433 lines of singleton. A column's worth of state is
module-scoped and cannot be instantiated twice:

- `installation`, `muted`, `master`, `ws` — **page** state, stays with the host.
- `surface` (the `ControlSurface` instance), `targetPicker`, `capturePreviews`,
  `pendingPreview`, `lastPresetReport`, `openCommandDevices` — **column** state,
  must become per-instance.
- `interacting` — **page** state, deliberately. The live-operator lens asked for
  this explicitly and `1` ratified the reasoning: nothing may move while a hand
  is on a control. Per-column suppression would let column B re-render under the
  operator's other hand while they drag in column A — and with overlapping
  targets, B is showing the value A is dragging. Freezing every column for the
  duration of a drag costs nothing (values are re-read on pointerup).
- `$("#cards")`, `$("#target-picker-host")`, `$("#event-status")` — document
  ids, must become host-relative element references. Note the app-wide-class
  ambiguity trap (CLAUDE.md gotcha 17): once there are two columns, a bare
  `.target-picker` resolves twice. Scope everything to the column root from the
  start.

This is the same shape `05c`/`05e` found in CSS — state and rules written onto
the surface instead of the component — one level up, in JS.

## The one thing that will bite — settle it HERE, not in `4`

From the `1-columns-design` consult (ratified 2026-07-31; see that stitch's
`judgment.md` §6.4). Two facts that pull in opposite directions:

- **One `ControlSurface` instance per column is required.** `openDrawers`,
  `drafts` (`control-surface.js:56-57`), `openSaveDrawers` and `saveExclusions`
  (`:266-267`) are all keyed by `scope:id` — the *target*, not the column. A
  shared instance would open the generator drawer for `seat:3` in every column
  showing seat 3.
- **But the fade animator is document-wide.** `animateFades` calls
  `document.querySelectorAll('[data-fade-anchor][data-automated="true"]')` at
  `control-surface.js:763`, and again at `:788` and `:792`. N instances start N
  rAF loops, each walking *every* column's anchors and writing their `input.value`
  and `output.value` — N× the work, racing each other.

**Resolve it in this stitch**: either scope those three queries to the instance's
bound root, or hoist the animator to a module singleton shared by all instances.
Either is fine; discovering it in `4` is not. The binders are already
parameterised (`bind(root = document)` at `:404, 828, 965, 971`), so
`facilitator.js:356`'s `surface.bind(document)` becoming `surface.bind(columnEl)`
is the cheap half.

Related, same cause: `bindPresets` looks a row up with
`root.querySelector('[data-preset-key="…"]')` (`:443`) where the key is
`scope:id`. Two columns carrying the same target — which `1` ruled **legal** —
produce two identical keys, and the second column's save drawer binds to the
first column's row. Passing the column root fixes it; nothing else does.

## Shape

Follow the house component idiom: `window.ControlColumn.create({host, ...})`,
like `window.TargetPicker.create` (`js/target-picker.js`) and
`window.ControlSurface.create` (`js/control-surface.js`). A new
`js/control-column.js`; if it needs its own rules, a component stylesheet
`css/control-column.css` (the app's fourth, after `value-box`,
`param-generator`, `target-picker`) rather than declarations in
`control-panel.css` — `05d`'s ownership guard
(`tests/test_css_component_ownership.py`) is browser-free and in `fast`, so it
will tell you.

The host passes in the send/apply adapters (`send`, `sendEvent`,
`sendAutomation`, the preset callbacks) and the state getter; the column owns
its picker, its cards, its transient preset state, and its own `interacting`
guard. Register the column as a component with the ownership guard.

## Not this stitch

- **Do not** retire the iframe or touch `index.html` — that is `3`.
- **Do not** add a second column, add/remove, or layout persistence — that is
  `4`, and it is gated on `1`.
- The `embedded` fork (`facilitator.js:3`, and its four consumers at `:125`,
  `:143`, `:200`, `:292`) may stay a constructor **option** on the column
  (e.g. `full: true` / `presets: true`) rather than a global read, which is
  what `3` will need. Do not try to resolve which host wins each fork here.
- The page furniture — `#master-row`, `#silence`, `#facilitator-commands`,
  `#venue-name`, `#ws-status`, `body.embedded` — is not the column's. Leave it
  in `facilitator.js`.

## Verify

`tools/run-tests.sh fast` and the full `browser` run, both green and
**unmodified**. If a journey needed editing, the extraction changed behaviour —
find out why before proceeding. Watch `47-live-param-kinds-flake` (a known
pre-existing intermittent under full-suite load) so you don't chase it.
