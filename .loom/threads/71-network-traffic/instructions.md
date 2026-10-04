# 71-network-traffic

**Goal:** the dashboard's background traffic stays small as the fleet grows —
on the installation Wi-Fi and to the browser.

**Status:** new (2026-10-03). Two design stitches; both end in proposals.
Bob asked for both. Evidence: `lore:2026-10-03-bopos-code-review-2026-10`
(§ Scaling concerns).

Why now: Kite Choir's Northern Broadwalk plan has 52 positions; shows run on
shared Wi-Fi where broadcast traffic is slow and costs everyone airtime.

## Stitches

1. `1-clock-sync-traffic` — keep sync quality, cut the per-device broadcast
   traffic. Touches the wire → Bob ratifies.
2. `2-monitor-transport` — the Monitor console streams every OSC message to
   every browser; design something that scales.

`69-complexity/2-split-osc-handle` should wait for `1` before restructuring
the sync code.

**Deferred (Bob, 2026-10-04):** clock-sync stage B (directed `/sync/query` with adaptive polling) from `1-clock-sync-traffic/proposal.md`. Revisit only if a real installation shows sync traffic still matters after stage A. Cheap probe to try in a hardware timing session first: a shared 0.5 Hz ping with unicast offsets.
