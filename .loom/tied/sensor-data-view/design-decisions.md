# sensor-data-view — build record (2026-07-08)

Built per the ratified proposal (`proposal.md`; Bob's ruling: Option A with
`role: "meter"`, consistent with the facilitator view's `role: "volume"`).

## What was built

- **Contract §11 note:** live values reach the fleet as outbound
  `/<id>/p/<name>` — patch republishes what it wants seen; framework-owned
  values a node is configured to expose ride the same surface. No new verbs,
  no subscription stream.
- **helper.py framework republisher:** `bopos.config` `METERS` (comma list,
  default empty = off) names sources from a small registry (`rssi`,
  `cpu_temp` today; I2C sources join the registry when hardware needs them);
  `METER_INTERVAL` (default 5 s, floor 1 s) throttles. Broadcasts
  `/<id>/p/<name> <float>` to `HB_TARGET:5550`, only when assigned.
- **Dashboard ingestion (`osc_bridge.handle_meter`):** attributes by id,
  validates the name, stores into a runtime-only `device["meters"]`
  (never durable, never in presets, never pushed back). Declared
  `role:"meter"` renders as a live bar+value in the params panel; an
  **undeclared** inbound name renders badged UNDECLARED (§8: a badge, not a
  guess); an inbound *control* name is ignored (not the meter surface).
  Client-bound "meter" ws messages are throttled to 5 Hz per (uid, name) and
  update the DOM in place — no full re-render per frame.
- **simfleet:** emits declared `role:"meter"` params every `--meter-interval`
  (0.5 s default, 0 disables) as a bounds-reflecting random walk, only while
  running with a live engine. Default manifest gained
  `{"name": "level", "role": "meter"}`.

## Judgment calls

1. Meter storage is separate from `params` (controls). That is what keeps
   meters out of installation.json, presets, and the declaration catch-up
   push by construction rather than by filtering.
2. Server→browser throttle is 5 Hz last-value-wins. Source-side rate remains
   the sender's responsibility (§12); the throttle just protects browsers on
   installation-scale fleets.
3. Cap of 32 distinct meter names per device so a misbehaving sender can't
   grow memory unboundedly.
4. Volume fallback (`gain`) now skips a param declared as a meter, both
   server- and facilitator-side.

## For Bob / real-rig

- **PD edit:** the default patch now *declares* a `level` meter but nothing
  PD-side sends it yet — a patch republishes a meter by sending
  `/<id>/p/level <value>` to 5550 (throttled; a few Hz is plenty). Until
  then the row shows "—" on real nodes (honest). simfleet emits it, so the
  sim dashboard shows live meters out of the box.
- helper.py `meter_loop` runs only on a Pi (needs 7770/6661 bindings to
  import); verified here at unit level (readers + config defaults + compile),
  needs a live-rig pass. Enable with `METERS=cpu_temp` in `bopos.config`.

## Verification

`verify_meters.py` — 9 checks, all passing: helper units, declared meter
renders read-only and updates live, undeclared badge, meters absent from
durable params and presets, facilitator unaffected. Regressions:
`verify_facilitator.py` (19) and `verify_patch_install.py` (9) still pass.
Screenshot `01-meters.png` in this stitch.
