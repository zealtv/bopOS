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
  `pendingPreview`, `lastPresetReport`, `interacting`, `openCommandDevices` —
  **column** state, must become per-instance.
- `$("#cards")`, `$("#target-picker-host")`, `$("#event-status")` — document
  ids, must become host-relative element references. Note the app-wide-class
  ambiguity trap (CLAUDE.md gotcha 17): once there are two columns, a bare
  `.target-picker` resolves twice. Scope everything to the column root from the
  start.

This is the same shape `05c`/`05e` found in CSS — state and rules written onto
the surface instead of the component — one level up, in JS.

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
