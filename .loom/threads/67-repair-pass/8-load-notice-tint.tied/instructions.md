# 8-load-notice-tint

**Status:** verified · small · Bob ruled 2026-10-03 ("tint the background")
**Goal:** the load-failure notice strip is hard to miss.

`6-load-failure-followups` (`55d769c`) added `#installation-notice`: plain
text over a thin amber rule (`dashboard/static/css/installation-notice.css`).
Bob wants the background tinted. Use an amber/warning tint from the existing
theme tokens (add one if none fits), readable in light and dark themes with
WCAG AA contrast for the text. No other change to placement, wording or
behaviour.

## Done when

- Light and dark screenshots (failed-load session) in this stitch, checked.
- `tests/verify_state_load_safety.py` still passes; fast tier green.
