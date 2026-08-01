# dashboard-bop-accents

> Reconstructed 2026-08-01 during the loom v1 → v2 migration. This stitch was
> authored and tied without an `instructions.md`; v2 requires one for every
> recognised record. The intent below is recovered from `notes.md` and
> `proposal.md`, which remain the authority for what was decided and shipped.

Keep the dark dashboard interface, but draw its accent colours from the bop
aesthetic (`bop.casio~`: lavender/periwinkle panels, ice-cyan value fields,
cream toggle, yellow warning) instead of the ad-hoc hexes scattered through
the stylesheets.

- Design pass produces `proposal.md`; open questions there are Bob's to rule on.
- Implementation is the safe core only: token block as dark/light/`data-theme`
  triples in both stylesheets, plus the hex migration for focus-visible
  outlines, selected/active states, spatial point handles, sim-device
  indicators, and Seat input focus.
- Out of scope by design: `--bg/--panel/--line/--text/--dim`, the green/amber/red
  semantics, `--auto`, the Okabe-Ito group swatches, the eight Show pill sets,
  and the slider/toggle accents.

Verification: `verify_bop_accents.py` in this stitch.
