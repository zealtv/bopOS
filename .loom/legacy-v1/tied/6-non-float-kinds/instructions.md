# 6-non-float-kinds

Fourth slice of the ratified control-panel design (authority: the tied
`2-control-panel-design` stitch — kind table in `control-panel-design.md`
§2).

- **Toggle** (int 0/1): latching button (`aria-pressed`, sharp radius)
  replacing the checkbox; under a generator it flashes its live value and
  wears the `--mod` border.
- **Integer**: right-aligned value box, step-1 slider, generators as today.
- **Enum**: manifest-declared options render as a select wiring an integer
  index; **automates like ints** (Bob's Q2 ruling) — the ∿ drawer applies,
  generators emit indices through the integer quantization path. Needs a
  manifest declaration shape for options — small additive manifest change,
  document it in the stitch.
- **Event**: render the ratified row (1–3 boxes at 58px + sync toggle +
  send momentary) for a manifest event declaration, **disabled** — the
  `<target>/e/*` wire plane is `44-event-plane`'s contract question; no
  `/e/*` messages are sent from this stitch.

Verify: living journeys for toggle/int/enum value + enum automation via
simfleet; event row render-only assertion.
