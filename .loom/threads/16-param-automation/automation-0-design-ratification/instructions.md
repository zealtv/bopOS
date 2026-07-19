# automation-0-design-ratification

**Ratified by Bob, 2026-07-19** — recorded in
`.lore/items/2026-07-19-param-automation-design-ratified/` (the full
ratification record, folding in `rulings-2026-07-19-round2.md` from this
directory). Draft and braindump remain in
`.lore/items/2026-07-19-param-automation-generator-design/`.

Remaining work for this stitch:

1. **Contract revision**: amend `docs/OSC-CONTRACT.md` — the automation
   grammar (string durations, `c:`/`p:`/`f` options with long aliases,
   `loop`, `stop`, `lfo` shapes, clock-anchored phase, int
   truncate-and-emit-per-crossing, catch-up semantics: fades as computed
   constants, sync LFOs verbatim) joins the §3 shorthand registry as
   framework-owned vocabulary on the `/p/*` plane; bump the revision table
   citing the ratified lore item. Note the deferred string/array kind
   (name and plane open) without speccing it.
2. **Decompose the implementation** into ordered child stitches of
   `16-param-automation` (sketch, adjust as needed): bopos.py generator
   engine + simfleet parity → show-tab builder GUI → animated controls +
   take-over → UX pass + waveform visualisation (Bob wants a UX-designer
   eye before implementing the viz — mark that gate `.waiting` when
   reached).
3. Tie this stitch; update CLAUDE.md thread-ordering if the decomposition
   changes it.

Ordering: `15-show-polish` runs first overall, but this stitch and the
dashboard-free implementation stitches (contract, engine, simfleet) are the
permitted interleave — they touch nothing the polish sweep touches.
