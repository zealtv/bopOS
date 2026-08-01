# 2-dual-route-transport

Implement explicit Dashboard transport ownership from the ratified design.

- Keep an execution destination that follows Live / Simulation / Patch Edit.
- Add an immutable physical-fleet LAN route on the existing framework port.
- Route every physical Devices-tab command through the physical path in every
  execution mode.
- Route master, MUTE ALL, parameters, automation, cues, and points through the
  execution path.
- Narrow mode guards so physical controls remain available during Simulation
  and Patch Edit while inappropriate execution/fleet deployment mutations stay
  guarded.
- Make execution restoration replay execution state only.
- Keep the current exact-device operation behavior intact at this seam; the
  positive Device enabled wire/state migration is owned by child stitch 3.

Preserve exact-UID targeting and acknowledgement honesty. Do not edit `.pd`
files.
