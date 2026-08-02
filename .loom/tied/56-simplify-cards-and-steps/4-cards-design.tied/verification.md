# Design verification

Checked on 2026-08-02 after Bob's review:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache \
  ~/.venvs/bopos/bin/python -m py_compile \
  .loom/threads/56-simplify-cards-and-steps/4-cards-design.stitching/mockup.py

OPENSSL_CONF=/dev/null \
PLAYWRIGHT_BROWSERS_PATH=/tmp/bopos-playwright \
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache \
  ~/.venvs/bopos/bin/python \
  .loom/threads/56-simplify-cards-and-steps/4-cards-design.stitching/mockup.py \
  .loom/threads/56-simplify-cards-and-steps/4-cards-design.stitching
```

The live path booted the dashboard and simfleet but macOS Chromium aborted at
launch because the managed sandbox hid its required `SystemAppearance` bundle.
The script's browser-free fallback then rendered shipping `ControlSurface` and
`TargetPicker` markup through current component styles and produced:

- `cards-control-1440-{dark,light}.png` — a persisted subset in four flexible
  tracks, add/close/single-target picker chrome, full manifest, PresetMenu, and
  All/group identity borders;
- `cards-remote-820-{dark,light}.png` — every All/group/Seat target in two
  evenly widened tracks, dashboard-only manifest subset, labels rather than
  pickers, identity borders, and no presets;
- matching self-contained HTML for detailed review.

All four PNGs were visually inspected. The group palette and patterns match the
Seats map (`#56B4E9` solid, `#E69F00` dashed, `#00B98B` dotted, and
`#CC79A7`/double); All has a thick white border with a dark backing keyline.
Cards overflow down, the page is the only shown vertical scrollport, Control's
second row demonstrates derived placement, and Remote cards are visibly
shorter. The static rasterizer does not paint browser-native range thumbs
exactly like Chromium; these images evidence hierarchy and layout, not pixel
parity or touch sizing.

No application source, state schema, server, OSC, Pure Data, or hardware was
changed or tested. This is the now-ratified design gate; implementation belongs
to `5-cards-implementation`.
