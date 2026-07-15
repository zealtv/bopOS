# 11-assets-device-workflow

Replace the Assets placeholder with an honest, useful workflow for managing
asset slots on one online assigned physical device at a time. Fleet-wide
desired assets, Sync All, rollout scheduling, and automatic coordinated engine
restarts are explicitly deferred to the separate `asset-fleet-distribution`
thread.

Accepted product direction and the deferred scale reasoning are retained in
`.lore/items/2026-07-15-asset-management-direction/`.

Children:

1. `11a-device-asset-inventory` — establish the minimum durable observation
   seam needed to know what asset slots a selected device has.
2. `11b-single-device-assets-workspace` — build the host catalog and explicit
   send/update/remove workflow for exactly one device.

Keep the ratified top-level `assets/<slot>/` deployment boundary. Slot names and
generation suffixes are operator-defined; contents below a slot remain opaque
and engine-neutral. Do not add a media taxonomy or archive transport here.
