# Design verification

Checked on 2026-08-02:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m py_compile \
  .loom/threads/56-simplify-cards-and-steps/4-cards-design.stitching/mockup.py

OPENSSL_CONF=/dev/null \
PLAYWRIGHT_BROWSERS_PATH=/tmp/bopos-playwright \
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  .loom/threads/56-simplify-cards-and-steps/4-cards-design.stitching/mockup.py \
  .loom/threads/56-simplify-cards-and-steps/4-cards-design.stitching
```

The live path booted the dashboard and simfleet but macOS Chromium aborted at
launch because the managed sandbox hid its required `SystemAppearance` bundle.
The script's browser-free fallback then rendered shipping ControlSurface markup
through current component styles and produced:

- `cards-control-1440-{dark,light}.png` — four fixed tracks, all → groups →
  Seats, full manifest and PresetMenu;
- `cards-remote-820-{dark,light}.png` — the same derived order in two tracks,
  with the existing dashboard-only manifest subset and no presets;
- matching self-contained HTML for detailed review.

All four PNGs were visually inspected. The cards overflow down, no horizontal
or nested card scroll is shown, the Control strip and target-picker/close/drag
chrome are absent, and Remote cards are visibly shorter. The static rasterizer
does not paint browser-native range thumbs exactly like Chromium; it is evidence
for hierarchy and layout, not pixel parity or touch sizing.

No application source, state schema, server, OSC, Pure Data, or hardware was
changed or tested. This is an unratified design gate.
