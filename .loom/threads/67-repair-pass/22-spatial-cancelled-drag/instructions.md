# 22-spatial-cancelled-drag

**Status:** ready
**Goal:** a cancelled pointer (pointercancel, lost capture) ends the drag on
both Spatial maps.

Evidence: `lore:2026-10-05-bopos-review-frontend` F4 (`spatial.js:353`). Today a cancelled pointer leaves the
map permanently dragging. Done when: a synthetic-pointer regression fails
before and passes after; Spatial journeys green. Touch hardware unverified.
