# dashboard-5-position-precision

Two dashboard improvements from Bob's seam-1 review (2026-07-11) — deliberately
**after** the current critical path (patch-seam, audition-rig); take as fill.

- [ ] **Numeric position entry:** set a device/element position by typing
      coordinates, not only by dragging on the SVG map (e.g. click-to-edit x/y
      fields on the selected item). Values flow through the same assign path
      as a drag.
- [ ] **Space origin / alignment:** a way to define the space with an origin
      (and implicitly units/orientation) so the dashboard layout can be
      aligned to other plans — floor plans, venue drawings. Persist in
      `installation.json`. Keep it minimal: an origin marker + offset is
      enough; don't build a CAD import.
- [ ] Playwright `verify_*.py` (copy newest tied dashboard verify as template;
      venv + gotchas in CLAUDE.md).

If seam-3 has landed multi-element positions by the time this is taken,
numeric entry applies per element (see Bob's element-dot UI note in
`patch-seam/seam-3-points-node-side/instructions.md`).
