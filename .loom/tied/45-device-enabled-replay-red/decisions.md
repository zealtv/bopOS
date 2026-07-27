# Decision

The persistent Device-enabled replay is real production behavior, not a missing
output-safety feature. `OSCBridge.handle()` has replayed
`state.device_enabled_for(uid)` whenever a physical device first appears or
returns from offline since `5eda7b4`.

The red was an environment-dependent test fake introduced by promotion:
`tests/test_device_control_routing.py` replaced only `bridge.sender`. The later
macOS routing change `54ff063` discovers the source route from a physical
heartbeat and may create `bridge.lan_sender`; on a host where the documentation
address is routable, that bypassed the recorder and left its frame list empty.
On a host where source discovery fails, the same test passed.

The fake now forces successful LAN-source discovery and routes every sender
created by the bridge back through the recorder. This exercises the dedicated
LAN-sender selection deterministically while retaining the original exact
`enabled 0` safety assertion.

## UI accordion check

The living accordion coverage is already appropriately placed in
`tests/verify_control_surface_component.py`. Its focused browser journey covers:

- open-by-default `<details>` / `<summary>` structure;
- 12 px child indentation and `▾` / `▸` disclosure glyphs;
- collapse by click;
- persistence across a heartbeat re-render and page reload;
- the exact scope + branch-path storage key;
- reopening and clearing the stored collapse.

No duplicate test was added.
