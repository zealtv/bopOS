---
name: finn-ciro-test-rig
description: The two real devices Bob is testing the device-scoped-patch workflow on — Finn Jet (fleet-node case) and Ciro Toast (standalone case)
metadata: 
  node_type: memory
  type: project
  originSessionId: 0d3948e4-d8b5-4914-9823-da1da5b27ef5
  modified: 2026-07-23T14:43:16.800Z
---

Bob's standing two-device rig for the device-scoped-patch / per-device-control
work (2026-07-24). Both are on one network and visible together in the
Dashboard:

- **Finn Jet** — a kite spool. Exercises bopOS as **one node of a large
  installation** (fleet member).
- **Ciro Toast** — a **standalone** device being set up to run on its own.

Use both to exercise every per-device behavior: targeting a patch to a single
device, drift vs the fleet patch, per-device live controls, and device-side
asset-pack removal. Finn Jet is also where the [[implementation-queue-status]]
node bug `36-engine-startup-delivery-race` was observed (2026-07-23 startup
race — engine port opened after the LAN listener, three provided-term sends
refused).

Relevant loom threads: `37-device-scoped-patch-control` (design, Bob-gated),
`38-patch-edit-chrome`, `39-remove-installed-pack-from-device`,
`36-engine-startup-delivery-race`.
