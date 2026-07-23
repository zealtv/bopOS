# 05-system-tab

The ratified `01-dock-design` keeps this tab in v1 scope.

Bob: "perhaps some other like system utility stuff that could be a tab down there
in a kind of like system overview inspector kind of thing."

## Outcome

- A system-overview tab: an at-a-glance read of the running system while a show
  is being built or run.
- The content list is `01`'s to decide. Candidates already available in the
  dashboard's state: fleet/heartbeat health, clock-sync status, WebSocket
  connection state, the loaded show and its persistence state, patch/manifest
  fingerprints, and the framework version. Prefer surfacing what already exists
  over adding new server-side telemetry in this stitch.
- Read-only. Anything actionable (restart, mute, update) already has a home on
  the Devices/Patches tabs — do not build a second control surface here.
- Must not add a new polling loop; ride the existing WebSocket state stream.

## Verify

Playwright against the real server + simfleet: assert the tab reflects a
simulated device going offline and coming back, and that no additional network
polling appears (`read_network_requests`-style check or a server-side request
count).
