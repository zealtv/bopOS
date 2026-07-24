# Proposal — per-device live-control placement & shape

Written 2026-07-25 (autopilot). **Awaiting Bob's ratification.**

- **Artifact (mockups):** https://claude.ai/code/artifact/6f9c395e-f7b0-43f3-b132-dbe1ebc2f780#p3
- **Source of record:** `../control-surface-proposals.html` (Proposal 03)

## Recommendation

Extract one reusable **`<ControlSurface scope patch>`** component (the param-tree
renderer + the value/gen row) and host it in three places differing only by
**scope** and **patch**: patch editor, Device tab (this device), Control tab
(All/Group/Seat). On the Device tab it sits **below diagnostics as a collapsible
panel**, which **retires the Seats-detail vertical-overflow complaint** rather
than patching it. The panel renders the device's *effective* patch (pin if
pinned, else fleet).

## Open questions Bob must settle
1. Default open vs collapsed on the Device tab (rec: collapsed, remembered).
2. Offline device: last-known read-only vs hidden.
3. Confirm the only seam between Device-write and All/Seat-fanout is `scope`, not two code paths.

**Feeds 01 & 04:** this component hosts the generator affordance (01) and is what
the Control tab (04) renders.
