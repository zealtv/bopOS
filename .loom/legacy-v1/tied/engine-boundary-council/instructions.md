# engine-boundary-council

Run a design-only `ai-kit` council session on the bopOS engine boundary. Use
`~/repos/ai-kit/skills/council-design-session/SKILL.md` exactly; keep all
artifacts in this stitch so they move to `tied/`.

Ground first in the actual repository. Required sources:

- `.notes/pd-engine-boundary-design-brief.md`
- `.lore/items/2026-07-11-pd-engine-boundary-brain-dump/`
- `docs/OSC-CONTRACT.md`
- lore `2026-07-10-patch-seam-council`
- tied `audition-0-port-spike`, `audition-1a-relay-launcher`,
  `audition-1b-pd-mac-gate`, and `seam-5-sc-starter-kit`
- current `pd/bopos.osc.pd`, `pd/bopos.out~.pd`, `python/helper.py`,
  `python/io/main.py`, `tools/audition.py`, and
  `templates/supercollider-bopos/`

First write `ground-truth.md` with verified facts and exact source paths. Then
write `session.md` and convene five independent experts in parallel:

1. **engine-api** — patch-author ergonomics and equivalent PD/SC/oF surfaces;
2. **transport** — UDP/process topology, throughput, meters, and IO streams;
3. **operations** — mute safety, boot/runtime failure, migration, and rig reality;
4. **creative-tools** — dashboard feedback, diagnostics, naming, and composition UX;
5. **simplifier** — challenge whether helper/PD relays, ports, and abstractions
   should exist in their current form; seek the smallest coherent model.

Experts must not read each other's files. Use a one-tier-down economical model
for expert seats and the strongest available model for the judge. If the five
designs converge without a meaningful crux, add one contrarian seat before the
judge. Each expert writes `expert-<lens>.md`; the judge reads every artifact,
re-checks load-bearing claims against the repo, and writes `judgment.md`.

The judge must rule on one path, explicitly reject alternatives, define the
stable engine-facing vocabulary and ownership model, quantify or bound traffic
where possible, and give a smallest reversible implementation slice. Also
produce `implementation-outline.md` describing proposed Loom changes, but do
not edit code, `.pd` files, the ratified contract, or implementation threads.

Done when all artifacts are durable, factual claims have source references,
the ruling is decisive enough for Bob to ratify, and remaining uncertainty is
named rather than hidden.
