# automation-0-design-ratification — worklog

2026-07-19, autopilot session (Fable orchestrator).

Bob had already ratified the design (recorded in lore
`2026-07-19-param-automation-design-ratified`, folding in this stitch's
`rulings-2026-07-19-round2.md`). This stitch executed the three remaining
items from its instructions:

1. **Contract revision — done.** `docs/OSC-CONTRACT.md` bumped 1.7 → 1.8:
   - new §3.2 "Parameter automation grammar (`/p/*` plane)": generator-slot
     model, arity shorthand, string duration units, `c:`/`p:`/`f` options
     with `curve:`/`phase:`/`free` aliases, keyword-lead/option-trail order,
     `loop`, `stop`, LFO shapes with clock-anchored idempotent phase and `f`
     free phase, int floor-and-emit-per-crossing, catch-up semantics (fades
     as computed constants, sync LFOs verbatim, free LFOs restart by
     design), decomposition-in-bopos.py boundary (engines unchanged).
   - `/p/*` planes-table row gains a §3.2 pointer; §15 gains the v1.8 row
     citing the ratified lore item and this stitch.
   - The deferred string/mixed-array kind is noted without being specced
     (name and plane explicitly open, per round-2 ruling 6).
2. **Decomposition — done.** Four ordered children laid under
   `16-param-automation`:
   - `automation-1-engine-and-parity` — bopos.py grammar/generator engine +
     simfleet parity; dashboard-free, may interleave with remaining
     `15-show-polish`.
   - `automation-2-show-builder-gui` — Show-tab builder compiling to the
     grammar (after 15-show-polish ties).
   - `automation-3-animated-takeover` — locally simulated animated controls
     + take-over across live-control surfaces; visualisation excluded.
   - `automation-4-waveform-ux-gate` — Bob-gated UX proposal for the
     waveform treatment; instructions mandate `.waiting` at the gate.
3. **CLAUDE.md — updated.** Contract references bumped to v1.8 (Start here
   item 2, foundation-status paragraph); program item 11 now records the
   tie and the child ordering.

Verification: documentation/planning stitch — verified by review against the
ratification record and round-2 rulings; no code paths changed.
