# 02-edit-bar-and-inline-step-name

Replace the current bottom add bar and inspector Arrange panel with one compact,
extensible edit bar immediately above the step-list scrollbox.

## Outcome

- Provide `+ Step`, `+ Divider`, Duplicate, and Delete in stable positions.
  Reserve flexible space/grouping for future lane/column actions.
- Keep it dense: use small text and/or familiar icons, with explicit accessible
  names, tooltips, keyboard focus, and touch-sized effective hit targets.
- Disable unavailable selection actions rather than shifting the bar. Define
  insertion and message-focus targeting exactly as ratified in
  `01-layout-review`.
- Duplicate the selected structural item through a real model/server operation;
  duplicated steps and nested messages receive fresh UIDs. Preserve persistence,
  second-client updates, undo, drag ordering, keyboard editing, goto integrity,
  and scroll-to-new-item behavior.
- Once feature parity exists, remove both `.show-add-bar` beneath the list and
  the Arrange section from step/divider inspectors.
- Replace the Step inspector's visible `alias` field with the step name as the
  bold inspector title. Click/tap enters inline edit; Enter or blur commits,
  Escape cancels, and blank maps to the existing untitled/null state. Keep the
  persisted `alias` field for schema compatibility, but call it **name** in the
  UI. Do not alter message aliases.

## Verification

Focused Playwright must cover desktop and 768px layouts, mouse/keyboard/touch
rename behavior, empty and populated shows, unambiguous action targeting,
fresh duplicate UIDs, persistence/second-client broadcast, undo, deletion,
drag/keyboard regressions, and no page-level horizontal overflow. Retain wide
and narrow review screenshots and run the adjacent Show editing/scrollbox
verifiers.
