# Verification — 8-load-notice-tint

2026-10-03. Reused `--warning-bg`, already defined for light and dark in both
dashboard and Remote theme stylesheets. Text retains `--text`; placement,
wording and behaviour are unchanged. No additional theme token is needed.

Passed:

- `./tools/run-tests.sh fast`: **380 tests, OK** (`fast.log`).
- `~/.venvs/bopos/bin/python -B tests/verify_state_load_safety.py --artifact-dir
  .loom/threads/67-repair-pass/8-load-notice-tint.stitching`: passed
  (`browser.log`). The journey now checks the rendered warning-token background
  and normal-text AA contrast in both themes on Control, Seats and Remote.
  Existing failed-load visibility, valid-load absence, reload and file-preservation
  checks also pass.
- `git diff --check`: passed.

Rendered text/background contrast is **14.12:1 light** (`#212529` / `#fff4dc`)
and **13.04:1 dark** (`#e8edf1` / `#2a241b`), exceeding 4.5:1 on all three
surfaces.

Visually inspected all six `notice-{control,seats,remote}-{light,dark}.png`
screenshots. The warning tint separates the strip from surrounding chrome;
text is legible, wraps without clipping, and appears once below the tab bar
or Remote header. Dashboard captures are 1280 × 900; Remote is 768 × 1024.
