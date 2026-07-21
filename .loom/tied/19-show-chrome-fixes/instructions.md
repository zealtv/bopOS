# 19-show-chrome-fixes

Four small Show-tab defects Bob hit while living with the tied
`18-show-chrome-density` work. Authorized by lore item
`2026-07-21-show-console-dock-and-fixes-braindump` (verbatim braindump in its
`content/`).

These are independent and small — take them in any order, one at a time.
None of them touch the show schema, playback semantics, or the message model.

Standing context: desktop-first app, but three of these four defects are
*narrow-viewport* defects, so verify at both widths. The Show tab's chrome
now runs on the `--chrome-*` variables shipped by `18-show-chrome-density/05`;
prefer adjusting those or Show-scoped rules over new one-off values.

Relevant code: `dashboard/static/js/show.js`, `dashboard/static/css/style.css`.
