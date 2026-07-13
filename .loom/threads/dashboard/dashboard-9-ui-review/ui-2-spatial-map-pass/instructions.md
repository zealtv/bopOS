# ui-2-spatial-map-pass

Spatial map interaction and rendering changes from the 2026-07-13 brain dump.

- [ ] **Listener heading as drag-dial:** the little circle on the heading
      line becomes the control — click-drag it like a dial. Remove the
      listener-heading number box from the UI.
- [ ] **Device/element dot opacity:** stop modulating dot opacity by point
      amplitude (breaks with many points or none). Instead a separate
      indicator per point, coloured to match the point — e.g. a dashed circle
      expanding around the point with its amplitude.
- [ ] **Point size/speed edits must not move the point:** changing size or
      speed currently disturbs position/trajectory — fix so those are
      orthogonal.
- [ ] **Clip points to the space:** points currently draw past the bounds of
      the space; obscure them beyond the bounds (SVG clip path).
- [ ] **Points list:** a list of points so one can be selected without
      clicking it on the map (moving points are hard to hit). Selection from
      the list behaves exactly like clicking the point.
- [ ] Playwright `verify_*.py`: heading drag changes heading (mind the drag
      gotchas in CLAUDE.md), dot opacity constant while a point's amplitude
      varies, size/speed edit leaves position unchanged, out-of-bounds point
      is clipped, list-selection selects.

Listener-puck *visibility* is settled: **sim-only**, ratified in
`dashboard-8-identity-sim-design` (tied), implemented by `d8-2-simulate-toggle`
(deferred). Don't implement visibility here; the drag-dial applies whenever
the puck is shown.
