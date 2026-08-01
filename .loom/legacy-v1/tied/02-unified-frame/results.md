# 02-unified-frame results

## Outcome

- Replaced the two independent Show-owned `<details>` consoles with one
  app-wide fixed **Monitor** frame.
- Moved high-rate `osc_in` / `osc_out` rendering from `show.js` into
  `monitor.js`, outside every tab panel and `#show-root`.
- Added one persisted collapse action, a persisted keyboard/pointer height
  resize, accessible traffic tabs, and app-wide placement.
- Preserved bounded buffers, batched rendering, independent wildcard/negative
  filters, pause, clear, counts, and auto-scroll.

The old tied console guards describe the superseded two-`details` structure.
The focused verifier here is the living authoring check for the new frame.

## Verification

```text
node --check dashboard/static/js/monitor.js
node --check dashboard/static/js/show.js
git diff --check
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/20-console-dock/02-unified-frame.stitching/verify_monitor_frame.py
```

Result: **10/10 passed** against the real Dashboard server plus simfleet in
headless Chromium. No browser errors. No hardware behavior is involved.
