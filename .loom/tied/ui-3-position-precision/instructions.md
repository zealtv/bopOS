# ui-3-position-precision

(Was `dashboard-5-position-precision`; moved into `dashboard-9-ui-review`
2026-07-13 per Bob's note below — take after ui-0..ui-2 so it's judged with
the rest of the review.)

**Bob, 2026-07-13:** do not take this as a standalone stitch. Integrate these
requirements into the broader dashboard UI review after functional work is in
place, so coordinate entry, spatial alignment, layout, legibility, and
interaction design are judged together.

Two dashboard improvements from Bob's seam-1 review (2026-07-11) — deliberately
**after** the current critical path (patch-seam, audition-rig); take as fill.

- [x] **Numeric position entry:** set a device/element position by typing
      coordinates, not only by dragging on the SVG map (e.g. click-to-edit x/y
      fields on the selected item). Values flow through the same assign path
      as a drag.
- [x] **Space origin / alignment:** a way to define the space with an origin
      (and implicitly units/orientation) so the dashboard layout can be
      aligned to other plans — floor plans, venue drawings. Persist in
      `installation.json`. Keep it minimal: an origin marker + offset is
      enough; don't build a CAD import.
- [x] Playwright `verify_*.py` (copy newest tied dashboard verify as template;
      venv + gotchas in CLAUDE.md).

If seam-3 has landed multi-element positions by the time this is taken,
numeric entry applies per element (see Bob's element-dot UI note in
`patch-seam/seam-3-points-node-side/instructions.md`).
