# 7-show-step-counts-cache

**Status:** ready
**Goal:** `state.public()` stops reading and validating every show file on
each snapshot.

Evidence: `lore:2026-10-05-bopos-review-show-model` F7 (3 snapshots × 5 shows = 15 loads). Cache step counts by
file identity (mtime/size) or update them when shows change. Done when: no
repeated loads for unchanged files; counts right after edit, create, copy,
rename, delete and an outside change; invalid shows still report `None`.
