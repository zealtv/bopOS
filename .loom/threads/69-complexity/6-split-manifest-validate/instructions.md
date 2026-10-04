# 6-split-manifest-validate

**Status:** after `67-repair-pass/12-manifest-boundaries`
**Goal:** `manifest.validate` (190 lines) reads as one public validator over
small private schema helpers (entry, params, events, IO, caps).

Evidence: `lore:2026-10-05-bopos-review-core-libs` F11. Delete the redundant `isinstance(manifest, dict)` after
`dict(candidate)`. No behaviour change: normalisation, error text and callers
stay as they are. Done when: no helper over ~60 lines; fast green.
