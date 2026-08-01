# ui-0-sidebar-fixes

Device sidebar fixes from the 2026-07-13 brain dump.

- [x] **ID assign spinner bug:** on an unassigned device the increment/
      decrement number box wouldn't move — it kept resetting to 6; Bob could
      only escape by decrementing to 3, after which incrementing past 6
      worked. Find the actual cause (likely value-clamp or stale-state
      feedback loop on the suggested-ID), don't just patch the symptom.
- [ ] **Suggested name from hostname:** when assigning an ID to an unassigned
      device, the suggested name should be pulled from the device hostname.
      NOTE (2026-07-13): hostname is not on the wire today; the additive
      `/os/report` hostname field was ratified in
      `dashboard-8-identity-sim-design` and lands node-side via dist-1/2
      (deferred). If this stitch is worked before that lands, do the spinner
      bug + blips and leave this item to `d8-3-binding-ux` (where naming
      moves to seat-binding anyway) — note the handoff here.
- [x] **Heartbeat blips:** visualise each device's heartbeat in the left bar —
      a little blip on the device row when its beat arrives.
- [x] Playwright `verify_*.py` on simfleet: assign flow with spinner
      + hostname suggestion, and a heartbeat blip assertion (class toggle or
      similar — don't try to screenshot-diff an animation).

Hostname handoff: the report field has not landed yet, and the seat model will
replace this device assignment form. Per the brief, hostname-based naming stays
with `d8-3-binding-ux` after `dist-1`/`dist-2` supply the field.
