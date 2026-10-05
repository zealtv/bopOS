# 23-control-listener-hygiene

**Status:** ready · low
**Goal:** Control re-renders don't leave stale gates or leak listeners.

Evidence: `lore:2026-10-05-bopos-review-frontend` F5, F6, F7.

- **F5.** Generator segment-removal gates go stale after row edits.
- **F6.** Rebinding the generator drawer stacks listeners on surviving nodes;
  bind once (fix together with F5).
- **F7.** Removed Control cards keep global target-picker listeners and their
  closures; release them on removal.

Done when: regressions fail before and pass after; Control journeys green.
