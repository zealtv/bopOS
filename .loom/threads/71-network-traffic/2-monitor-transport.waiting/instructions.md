# 2-monitor-transport

**Status:** ready · design, then build · operator-visible changes need Bob
**Goal:** the Monitor console shows what an operator needs without streaming
every OSC message to every browser.

Bob, 2026-10-03: *"there's likely a better networking design for the monitor
also."*

## Today

`OSCBridge._send_to` and `OSCBridge.handle` broadcast every outbound and
inbound OSC message (`osc_out` / `osc_in`) to every connected browser, each
through its own `asyncio.create_task`. Filtering is client-side. Heartbeats,
sync pings/pongs/offsets and 25 Hz `/pt` frames all go to every open tab,
whether or not the Monitor is open. Cost grows with nodes × browsers.

## Design questions

- **Subscribe on demand:** only clients with the console open receive the tap;
  they say what they want (address prefixes, device, direction).
- **Filter server-side**, and keep high-rate classes (sync, `/pt`, heartbeats)
  out by default — summarised as rates rather than individual lines.
- **Batch:** one websocket frame per ~100 ms instead of a task per datagram.
- **Bound it:** a per-client cap with a visible "N messages dropped" line, so a
  slow browser can't back up the dashboard.
- Check what else is per-datagram broadcast (`heartbeat`, `sync`,
  `point_frame`, `device_update` on every beat) — the same treatment may apply.

## Deliver

A short proposal (with measured message rates on simfleet at 50 nodes), then
the build. Any change to what the console shows by default goes to Bob first.
