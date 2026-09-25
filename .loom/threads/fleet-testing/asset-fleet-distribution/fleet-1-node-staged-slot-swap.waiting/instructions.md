# fleet-1-node-staged-slot-swap

**Status:** waiting — optional hardening, parked 2026-07-15. Independent of
`fleet-0`; claim ahead of it if needed.
**Resume when:** the live-slot warning in Assets proves insufficient, or before
fleet work builds on slot activation.
**Goal:** asset-slot updates on the node are atomic — no partially updated live
folder.

## Change

- Fetch into a staging dir beside the slot (`assets/.staging-<slot>-*`),
  hardlinking unchanged files from the installed slot, then verify and
  `os.replace` swap with backup. Same pattern as patches in
  `python/fetcher.py` (`_patch_fetch`), using hardlinks instead of `copytree`.
- **No wire change** (contract §7 fixes *what*, not *how*). Cache seeding must
  point at final paths, not staging.
- Update the Assets warning: "mutates the live directory" becomes "files swap
  under a running engine at completion".

## Done when

Non-browser test covering: interrupted fetch leaves the slot untouched;
successful fetch swaps completely; unchanged files aren't re-downloaded; an
engine holding a file open keeps playing through the swap. Note actual disk
overhead.
