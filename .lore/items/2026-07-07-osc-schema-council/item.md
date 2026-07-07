# Council: the bopOS OSC schema contract — designs, judgment, ratification

The council-design-session of record for `docs/OSC-CONTRACT.md` v1.0. Five
independent experts (protocol design, distributed systems, platform agnosticism,
performer/artist workflow, simplicity guard — all on opus) each designed the OSC
contract from verified ground truth; a judge (fable, inline) re-verified the
load-bearing facts against the code, named the two cruxes (assignment authority;
the framework/patch boundary as a wire token with a patch manifest as keystone),
and ruled a synthesis. Bob ratified 2026-07-07 with amendments: node-side
persistence is required and standalone (network-removed) operation is first-class;
addresses get registered shorthands (`/pt`, `/hb`) for high-rate traffic; dashboard
scenes may emit arbitrary OSC beyond the contract; `/os/mute` is safety-critical
and spam-safe.

## Source

Loom stitch `osc-schema-contract/schema-design-draft` (bopOS loom), run with the
ai-kit `council-design-session` skill across two sessions on 2026-07-07 (the first
was dropped at the judge step by a usage limit; artifacts recovered from its
scratchpad).

## Outcome

`docs/OSC-CONTRACT.md` v1.0 landed; implementation split into sibling stitches in
the `osc-schema-contract` thread. Read `content/ratification.md` for Bob's rulings,
`content/judgment.md` for the ruling and its reasoning, `content/session.md` for
the roster and spread.

## Tags

- council
- osc
- contract
- design
