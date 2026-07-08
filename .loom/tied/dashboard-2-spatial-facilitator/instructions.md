# dashboard-2-spatial-facilitator

Phase 2 of `.notes/dashboard-development-context.md`: the spatial map and the
facilitator view.

Checklist:
- [ ] SVG top-down spatial map: devices as draggable circles, drag-to-position writes
      pos into `installation.json`; colour = online status; click to select
- [ ] Facilitator view `/facilitator`: per-device volume cards, master volume,
      Silence All, Start All, preset picker — touch-first for iPad, PWA manifest
- [ ] Preset system: save/load named partial states

Notes:
- The spatial map is also the authoring surface for `spatial-audio` later — keep the
  coordinate system explicit (units, origin, room bounds stored in `installation.json`).
- Positions already exist in the data model (`bopos.devices` POSL/POSR, pos1/pos2).
