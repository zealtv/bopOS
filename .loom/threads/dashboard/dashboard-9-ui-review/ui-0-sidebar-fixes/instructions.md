# ui-0-sidebar-fixes

Device sidebar fixes from the 2026-07-13 brain dump.

- [ ] **ID assign spinner bug:** on an unassigned device the increment/
      decrement number box wouldn't move — it kept resetting to 6; Bob could
      only escape by decrementing to 3, after which incrementing past 6
      worked. Find the actual cause (likely value-clamp or stale-state
      feedback loop on the suggested-ID), don't just patch the symptom.
- [ ] **Suggested name from hostname:** when assigning an ID to an unassigned
      device, the suggested name should be pulled from the device hostname.
- [ ] **Heartbeat blips:** visualise each device's heartbeat in the left bar —
      a little blip on the device row when its beat arrives.
- [ ] Playwright `verify_*.py` on simfleet: assign flow with spinner
      + hostname suggestion, and a heartbeat blip assertion (class toggle or
      similar — don't try to screenshot-diff an animation).
