# dashboard-light-status-badges

Complete the light-theme status treatment exposed by Bob's 2026-07-20 Seat
roster screenshot.

- Audit operational status pills and notices shared by Seats, Devices, Patches,
  Assets, and Show transport.
- Introduce paired semantic success/warning/danger/neutral status surfaces.
- Use pale surfaces with readable dark text in light mode while preserving the
  established dark-theme palette.
- Cover patch-current/stale/switching badges, asset current/stale/unknown/error
  states and inventory notices, device mute state, Show running/paused state,
  and inline validation notices that use the same dark-only treatment.

Verify representative status families and text contrast in a real browser,
retain a light review screenshot, preserve Bob's untracked `dashboard/shows/`,
and do not edit `.pd` files.
