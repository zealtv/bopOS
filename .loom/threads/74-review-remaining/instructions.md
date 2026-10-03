# 74-review-remaining

**Goal:** finish the October review — the parts it didn't cover in depth get
the same look, and their findings go to lore and the loom.

**Status:** new (2026-10-03). The first pass is `lore:2026-10-03-bopos-code-review-2026-10`; its "Not reviewed in
depth" list is this thread.

Each child: read the code, run what's runnable, and deliver findings as an
addendum lore item (new capture, not an edit) plus stitches for anything worth
doing — bugs into `67-repair-pass` style children, cleanup into `70`,
structure into `69`. Same rule as the first pass: confirm bugs by
reproduction where possible, and label the rest *likely*.

## Stitches

1. `1-review-core-libs` — `manifest.py`, `paramgen.py`, `identity.py`,
   `fetcher.py`, `points.py`/`pointfield.py`, `sync_node.py`, `store.py`.
2. `2-review-frontend-modules` — `control-surface.js`, `control-column.js`,
   `spatial.js`, `monitor.js`, `target-picker.js`, CSS.
3. `3-review-install-and-services` — `install-device.sh`,
   `install-dashboard.sh`, `run.sh`, `bash/provision.sh`, systemd units,
   sudoers helpers, `start-engine.sh`.
4. `4-review-show-model` — `show_model.py` after presets are gone.
