# 2-split-osc-handle

**Status:** ready · easier after `68-remove-git-patch-route` and `65`
**Goal:** inbound OSC handling in `dashboard/osc_bridge.py` is a dispatcher
over one small handler per address.

## Today

`OSCBridge.handle` (`osc_bridge.py:1109`) is 546 lines; the `/hb` branch alone
is ~150 and carries assignment replay, unassign repair, group convergence,
live-param replay, enabled re-assertion and editor setup. `osc_bridge.py` is
1,764 lines mixing transport, request/reply bookkeeping, fetch generations,
clock sync, points and group convergence.

## Shape

- Address → handler table; the heartbeat path split into named steps.
- Consider splitting the file by concern (transport; request/reply tracking;
  fetch generations; group convergence; sync). Clock sync may be redesigned by
  `71-network-traffic/1-clock-sync-traffic` — coordinate, don't polish code
  that's about to change.

## Done when

- No handler over ~60 lines. Fast + browser green; no behaviour change.
