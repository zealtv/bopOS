# 15-store-temp-files

**Status:** ready
**Goal:** writing one store key never touches another.

Evidence: `lore:2026-10-05-bopos-review-core-libs` F8. `python/store.py` writes through `<key>.tmp`, which is
itself a valid key: putting `assignment` destroys `assignment.tmp`. Use a
private unique temp name outside the key namespace (e.g. `tempfile` in the same
dir); keep the key API. Done when: the collision test fails before, passes
after; fast green.
