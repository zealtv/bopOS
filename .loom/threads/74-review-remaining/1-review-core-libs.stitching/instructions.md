# 1-review-core-libs

**Status:** ready
**Goal:** review the shared Python libraries both node and dashboard depend on.

Scope: `python/manifest.py` (its `validate` is 190 lines), `python/paramgen.py`,
`python/identity.py`, `python/fetcher.py` (path guards looked sound in the
first pass — confirm), `python/pointfield.py`, `dashboard/points.py`,
`python/sync_node.py`, `python/store.py`, `python/groups.py`, `python/relay.py`.

Look for: correctness at edges (empty, huge, malformed input, 32-bit float
limits — `glean:pd-float-precision`), duplication between node and dashboard
copies, dead code, and functions that are hard to follow. Deliver as the parent
says.
