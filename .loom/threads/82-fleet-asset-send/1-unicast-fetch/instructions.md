# 1-unicast-fetch

Send `/<id>/os/fetch` to the device's own IP, not the physical broadcast
address. The message is the same, so this isn't a contract change.

## Why

On 2026-10-27, Eden Pearl missed two broadcast patch fetches during the
`kc-test` push and sat at "switching". The same datagram sent straight to
192.168.0.102:6660 worked at once. Broadcasts on the Pi Wi-Fi seem lossy
(see `79-wifi-power-save`). Clock-sync pings already go unicast.

## Do

- `OSCBridge._send_fetch_generation` (`dashboard/osc_bridge.py`) currently
  calls `send_physical(...)`, which goes to the broadcast destination. When
  the device is physical and has a known heartbeat `ip`, send to
  `(ip, send_port)` instead; otherwise fall back to broadcast. Reuse the
  bridge's sender and transport-error reporting (`_send_to`), so the
  monitor's `osc_out` tap still shows the send with its real target.
- This covers patch pushes too (`converge_fleet_patch` and retries share the
  function). That's intended.
- If the device's IP changes between heartbeats, the next send uses the new
  one. The attribution of replies by IP (`_fetch_record`) is unchanged.
- Check whether the monitor and tests assume broadcast for fetch
  (`tests/test_fetch_generations.py`, `test_node_fetch_dispatch.py`,
  `tools/simfleet.py`). The simfleet peers must still receive the fetch;
  they may bind per-peer addresses or a shared one, so check.

## Verify

- A unit test: a physical device with `ip` gets the datagram at that IP; one
  without an IP (or a virtual one) falls back.
- The existing fetch and patch-push tests still pass, plus a simfleet patch
  push in the browser tier.
