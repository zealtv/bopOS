# Handoff — device alias design ratified (2026-07-16)

This supersedes `.notes/handoff-2026-07-16-assets-hardware-repair-complete.md`.

## Current state

- Assets single-device delivery, real `bop000` repair, and compatibility-path
  retirement remain complete at `44b184a`.
- Bob brought the later device-alias decision gate forward and ratified it.
- The complete design is retained in
  `.lore/items/2026-07-16-device-alias-design-ratified/`.
- `Freda Sparks` anchors the two curated lists. Given names are globally broad,
  ASCII-only, short and readily pronounced in English. Character surnames are
  vivid non-name words with pop-star energy. Forget deletes the registry entry.
- This was design-only; no registry or UI implementation landed.

## Next choice

The previously accepted next implementation stitch remains
`12-dashboard-live-controls`. Because aliases will feed its target labels, the
ratified proposal recommends landing a device-alias implementation follow-up
before or with Live Controls rather than introducing another hostname-first
surface. Bob should choose between that implementation follow-up and returning
directly to Live Controls.
