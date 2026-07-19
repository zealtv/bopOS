# Parameter automation design — ratification record

Bob ratified the parameter-automation generator-slot design on 2026-07-19,
same day as the braindump and both design rounds.

## What is ratified

The draft proposal in
`.lore/items/2026-07-19-param-automation-generator-design/content/design-proposal.md`
**as amended by the second-round rulings** (preserved in the
`automation-0-design-ratification` stitch as `rulings-2026-07-19-round2.md`,
travelling with it into `tied/`). In summary:

- **Generator-slot model.** One generator slot per numeric `/p/*` param:
  constant, finite fade (single- or multi-segment), `loop` (replays the
  segment list, snapping back to its start), LFO, `stop` (freeze at current
  output). Last message wins — any message replaces the generator; no
  layering, no modulation routing. Touching a dashboard control sends a
  plain value and thereby takes over.
- **Fade grammar** = bop's arity shorthand, kept: 1 elem set; 2 elems go-to
  in dur; 3 elems from/to/dur; 4+ even elems dest/dur pairs from current;
  odd ≥5 error. Bare numeric durations are ms (legacy); string durations
  `250ms` `10s` `1.5m` `2h`. Musical units are dropped from the wire
  entirely — the authoring layer compiles beats/bars to ms at send time
  (transport design stays with `scene-sequencing`).
- **Curve**: one trailing signed-exponent token per message, `c:<n>`
  (long alias `curve:<n>`); 0/omitted linear, >0 ease-in-ish, <0
  ease-out-ish. No per-segment curves (Bob: not needed).
- **LFO**: `/param lfo <shape> <min> <max> <period> [p:<0..1>] [f] [c:<n>]`
  with shapes `sine tri saw square sh drift`. Phase is clock-anchored to
  the sync plane by default — `((t_synced / period) + phase) mod 1` — making
  LFO messages full-state and idempotent; `f` (free) opts into per-device
  random phase for decorrelation.
- **Option shorthand**: `c:` `p:` `f` are canonical on the wire (bandwidth;
  OSC 4-byte string padding); `curve:` `phase:` `free` accepted as
  hand-typed aliases. Keywords lead, options trail.
- **Ints**: interpolate continuously, truncate (floor), emit exactly once
  at each integer crossing, in either direction.
- **Control-plane law preserved**: sync LFOs are idempotent and catch up by
  verbatim replay; free LFOs restart phase on resend by design; fades catch
  up as the computed current value (a constant), and a completed fade's
  destination is the stored full-state value.
- **Decomposition in bopos.py**, not PD: Python owns parsing, units,
  curves, scheduling, phase math, and the catch-up "value now". PD engines
  receive only the existing go-to-x-in-y-ms primitive (segment boundaries;
  ~30–50 Hz smoothing segments for LFOs — "fine for now until it isn't").
  64-bit time never enters PD; existing patches need zero changes. This is
  the `/pt` node-side-decomposition precedent, not the reverted `/p/gain`
  composition.
- **Show tab & dashboard**: message-builder GUI compiles to this grammar;
  automated controls animate by local simulation (dashboard knows the
  generator and the synced clock — zero extra wire traffic); waveform
  visualisation doubles as the automation indicator and fades out on touch
  — gated on a UX-designer pass before implementation.

## Explicitly deferred (noted, not decided)

- Strings and mixed arrays as a **non-param manifest kind**: name open
  ("atom" felt wrong for multi-part values; candidates attribute,
  property), plane open (`<selector>/p/*` vs its own `<selector>/a/*`).
  Set-only, full-state, grammar keywords never apply. Own stitch later.
- Musical time / tempo on the wire (with `scene-sequencing`); per-segment
  curves (dropped); square `duty:`; audio-rate modulation (patch-internal).

## Contract impact

- §3 shorthand-registry revision: the automation grammar becomes
  framework-owned vocabulary on the `/p/*` plane; output semantics remain
  patch-owned. Catch-up note: fades as computed constants, sync LFOs
  verbatim.
- The deferred string/array kind will be its own additive amendment when
  its stitch runs.

## Ordering

Thread `16-param-automation` runs after `15-show-polish` (bugs first; its
GUI stitches touch the same panels). Permitted interleave: the
dashboard-free stitches — contract amendment, bopos.py generator engine,
simfleet parity — may run in parallel with remaining polish. The
`patch-workflow-friction` docs resume lands after this thread.
