# 38-patch-edit-chrome

Tidy the Patch Edit chrome so the mode switch drives the editor and the
edit-session controls carry their weight. Bob's directives, 2026-07-24.

The menu-bar execution-target switch is the three buttons Live Fleet /
Simulation / Patch Edit (`dashboard/static/index.html:6`,
`data-execution-target` off / simulate / edit). The editor launch/session
controls live in the Patch tab (`index.html:83` and the `renderEditor()` block
`dashboard/static/js/dashboard.js:701`).

Two children, workable independently:

1. `1-mode-switch-launches-editor` — Patch Edit button launches the editor;
   leaving the mode closes it.
2. `2-edit-session-button-cleanup` — remove three controls, rename Stop, and
   swap it in for Launch editor while editing.

These are directed UI fixes, not a design gate. Keep simulator parity and
update/adjust the relevant Playwright coverage.
