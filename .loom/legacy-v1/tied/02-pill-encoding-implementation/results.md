# 02-pill-encoding-implementation results

## Outcome

- Replaced alias hashing with eight ratified flat categories: cue, point, raw,
  param-value, param-fade, param-loop, param-lfo, and param-stop.
- Added visible redundant codes (`CUE`, `PT`, `RAW`, `VAL`, `FD`, `LP`, `LFO`,
  `STOP`) plus expanded accessible names.
- Added semantic theme tokens for every category. Category classes set only
  foreground/background; the existing neutral border and focus/drop
  box-shadows retain their jobs.
- Moved the message label into its own ellipsizing span so the kind code never
  disappears under narrow truncation.
- Removed `PILL_PALETTE_SIZE`, `.show-pill-0..7`, and both themes' old numeric
  palette rules completely.

## Verification

```text
node --check dashboard/static/js/show.js
node --check dashboard/static/js/monitor.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/25-message-pill-encoding/02-pill-encoding-implementation.stitching/verify_semantic_pills.py
git diff --check
```

Result: **24/24** real-server + simfleet Playwright checks passed. The verifier
uses one fixture message per category, checks semantic classes/codes and
accessible names, proves eight distinct computed fills in dark and light,
checks that the theme token sets differ, exercises focus/drop/drag coexistence,
asserts no numeric hash class remains, and records no browser errors.

Review screenshots:

- `semantic-pills-dark.png`
- `semantic-pills-light.png`

The token table's measured text contrast remains 9.32:1–11.05:1 dark and
6.22:1–7.30:1 light.
