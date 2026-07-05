# dashboard-4-patch-mgmt

Phase 4: patch and framework management from the dashboard — this is the main
friction-killer for working with non-technical musicians (review §3.6).

Checklist:
- [ ] Patch panel per device + fleet-wide: current patch, switch (`/patch`),
      add from GitHub (`/addpatch <user> <repo>`), pull (`/pullpatch`), get samples
- [ ] Framework update: `/os/update` per device and `/all`, with per-device version
      display so a half-updated fleet is visible
- [ ] Sensor data view: live per-device I/O values (needs the Pi to expose them —
      coordinate with `osc-schema-contract`; today 6662 is localhost-only)
- [ ] Installation file management: save/load/switch `installation.json` per venue

Stretch: scheduled presets (time-of-day automation), TouchOSC bridge port.
