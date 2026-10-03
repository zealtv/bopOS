# 70-dead-code-sweep

**Goal:** code nothing uses is gone, and the docs name files that exist.

**Status:** new (2026-10-03). Both children ready. Evidence:
`lore:2026-10-03-bopos-code-review-2026-10` (§ Dead or stale code).

## Stitches

1. `1-dead-code` — orphan websocket verbs, unused methods, superseded scripts,
   leftovers, pyflakes warnings.
2. `2-doc-drift` — doc references to files that moved.
