# 34-fleet-patch-global-state

**Status:** parked by Bob, 2026-07-23 · Bob-gated design first
**Goal:** show "the fleet patch" as global state in the dashboard menu bar,
visible from every tab.

Bob, 2026-07-23: *"generally there'll be a patch that is the fleet patch, and
that's like a global state that we need to be aware of globally on the
dashboard. So that's probably something that needs to be up in the menu bar."*

## Questions

- **Define or display?** Is "the fleet patch" a new first-class target, or a
  projection of what bound nodes are converging on? The dashboard already has a
  live fleet patch (`live_fleet_patch`) plus per-device pins (`58`) — settle
  whether this thread defines anything new or just surfaces it.
- **What it shows:** name, fingerprint tail, convergence (all current / N
  drifting / unknown / offline).
- **Actionable or display-only?** If actionable: path and confirmation.
- **Plumbing:** computed server-side, reaches the header without coupling to one
  tab.

Coordinate with `58-patch-push-workflow` (pins and push affordances) and
`fleet-testing/asset-fleet-distribution` so the fleet patch is defined once.

## Stitches

1. `1-menubar-fleet-patch-design` — proposal for Bob.
