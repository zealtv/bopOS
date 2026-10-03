# 69-complexity

**Goal:** the review's complexity hotspots are each taken apart, so the code is
easy to read and change — Bob: *"simplify the code base."*

**Status:** new (2026-10-03). Evidence:
`lore:2026-10-03-bopos-code-review-2026-10` (§ Complexity hotspots).

## Order matters

Remove before restructuring. `65-remove-presets`, `68-remove-git-patch-route`
and (later) the pin removal from `66-projects` each delete a large slice of
`server.py` and `osc_bridge.py`. Splitting those files first would mean moving
code that's about to be deleted. `1` is anchored on `65/2` and `68`; the rest
can start any time.

## Every review point, and where it's handled

| review point | stitch |
|---|---|
| `handle_ws`: 1,093 lines, 89 branches | `1-split-handle-ws` |
| `OSCBridge.handle`: 546 lines | `2-split-osc-handle` |
| three node implementations drifting apart | `3-shared-node-protocol` |
| a second distribution route via Git | `68-remove-git-patch-route` |
| `send_to_engine` defensive wrappers; duplicated cache warming | `4-node-daemon-tidy` |
| dense `dashboard.js` | `5-dashboard-js-readability` |
| pinning machinery | `66-projects/0-project-design` (named there for deletion) |

## Constraints

- Behaviour-preserving: each stitch changes structure, not behaviour, and says
  so in its commit. Fast + browser tiers green before and after.
- Small slices that each commit (`glean:land-before-usage-limit`).
