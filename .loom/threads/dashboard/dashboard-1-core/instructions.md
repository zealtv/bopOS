# dashboard-1-core

Replace DASHBOARD.pd's core function with the web dashboard (Phase 1 of
`.notes/dashboard-development-context.md` §13).

Checklist:
- [ ] `dashboard/` dir per the design doc file structure (server.py, state.py, osc_bridge.py, static/)
- [ ] FastAPI server: OSC listen 5550, OSC broadcast send 6660, WebSocket hub, static serving
- [ ] Device list with online/offline from heartbeat tracking (correlate by source IP; ~30s timeout)
- [ ] Per-device controls: gain, gain2, backing, echo; actions: reboot, shutdown, update, getsamples, aloha
- [ ] `/all/*` broadcast variants
- [ ] State persistence to `installation.json`; import `bopos.devices` to seed the device map
- [ ] Dark, responsive UI

Caveat (Bob, round 2): gain/gain2/backing/echo are **patch-specific**, not framework —
phase 1 replicates them for parity with DASHBOARD.pd, but build the controls panel as a
generic "parameter list" component so it can switch to contract-discovered patch
parameters once `osc-schema-contract` lands. Don't bake the three sliders in deep.

Done when: a real installation can be monitored and mixed from a browser with
DASHBOARD.pd closed, using unmodified Pis.
