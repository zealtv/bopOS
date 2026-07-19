# automation-1-engine-and-parity

The bopos.py generator engine plus simfleet parity — the wire-visible half of
the ratified generator-slot design (contract §3.2, v1.8; reasoning in lore
`2026-07-19-param-automation-design-ratified`). **Dashboard-free: this stitch
may interleave with remaining `15-show-polish` work.**

Scope:

1. **Grammar parser** (bopos.py): the full §3.2 vocabulary on numeric `/p/*`
   params — arity shorthand (1/2/3/even-list; odd ≥5 = loud error), string
   durations (`250ms` `10s` `1.5m` `2h`, bare number = ms), `loop`, `stop`,
   `lfo <shape> <min> <max> <period>` with shapes `sine tri saw square sh
   drift`, trailing options `c:<n>` `p:<0..1>` `f` plus long aliases
   `curve:` `phase:` `free`. Keywords lead, options trail. Grammar applies
   only to manifest-declared numeric params; string params stay plain
   set-only.
2. **Generator slots**: one per param address, last message wins. Segment
   scheduling with curve exponent; loop snap-back; `stop` freezes at
   current output; LFO phase clock-anchored to the sync plane
   (`((t_synced / period) + phase) mod 1`), `f` = per-device random phase.
3. **Decomposition to the engine**: emit only the existing selector-free
   go-to-x-in-y-ms primitive at segment boundaries; ~30–50 Hz smoothing
   segments for LFOs. No 64-bit time to PD, no new engine surface, zero
   patch changes.
4. **Int semantics**: continuous interpolation, floor, emit exactly once per
   integer crossing, either direction.
5. **Catch-up**: the catch-up path reports fades as the computed current
   constant; completed fades store their destination as the full-state
   value; sync LFOs replay verbatim.
6. **Simfleet parity in the same stitch** (house rule): tools/simfleet.py
   speaks/receives the same grammar so dashboard stitches can be developed
   against it.

Verify: browser-free (LAN/engine planes) — drive bopos.py (or its module)
plus simfleet from a Python harness; assert segment streams, int crossings,
loop snap-back, LFO phase determinism given a fixed synced clock, take-over
by plain value, and catch-up values. `~/.venvs/bopos` venv per
`docs/VERIFICATION.md`.

Split if it fights back (parser / scheduler / parity are natural children).
