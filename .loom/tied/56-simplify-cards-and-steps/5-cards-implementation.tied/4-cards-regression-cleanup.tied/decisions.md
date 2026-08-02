# Regression decisions

- `tests/verify_control_column_scroll.py` stays living but now guards the
  inverse behavior: equal flexible tracks, no nested scrollport, document
  growth, and page-scroll reachability on Control and Remote. Deleting it would
  lose the measured regression seam that originally exposed unreachable rows.
- Persistence migration and derived ordering moved into the DOM-free
  `ControlCardsModel`; browser-free tests execute that actual helper in Node.
- Static CSS/capability checks complement—not replace—the focused Playwright
  journeys. They make the required track grammar, page-scroll ownership, and
  Remote/Control capability split part of the fast tier.
- CLAUDE gotcha 19 is marked superseded for Control: targets are unique card
  membership and runtime picker ids are no longer persisted. Gotcha 20 remains
  valid because fragment navigation still does not reload persistence.
