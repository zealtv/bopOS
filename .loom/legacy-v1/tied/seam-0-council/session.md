# Session — bopOS↔patch seam council (2026-07-10)

Skill: ai-kit `council-design-session`. Stitch: `patch-seam/seam-0-council`.
Frame confirmed by Bob in-session: five seats (facilitator-UX seat dropped as
lower priority — promotion stays in scope via the protocol + boundary seats);
depth = principles + concrete sketches; multi-element = design it, stage it.

## Roster

All experts: **opus**, general-purpose agents, repo read access, design-only
(no code, one artifact file each). Judge: **fable, inline** (orchestrator),
per the precedent of the 2026-07-07 OSC council. Bob ratifies after.

| seat | file | mandate |
|---|---|---|
| Framework boundary | `expert-framework-boundary.md` | What a framework owns vs. hosts vs. merely offers; provided/subscribed/enforced as an API stance; test every current coupling against it. Precedents: plugin hosts, SC server/client, the web platform. |
| Protocol designer | `expert-protocol-designer.md` | The wire and the manifest: where provided values live in the grammar, promotion metadata, element addressing. Output shaped like contract amendments. |
| Patch author | `expert-patch-author.md` | The seam from inside a PD/SC/OF patch: what subscribing feels like, what every patch must now implement itself (master gain!), boilerplate vs. freedom, what the starter kit teaches. |
| Ops reality | `expert-ops-reality.md` | The constraint that invalidates elegant designs: Pi Zero 2 W, N engines per device (ports, jack/alsa, pid model, engine-alive bit), mute independence, broadcast rates, standalone mode, migration. |
| Simplicity guard | `expert-simplicity-guard.md` | How much redesign is actually warranted; what NOT to build; smallest contract delta that fixes the actual mistake; guard against speculative generality and manifest bloat. |

## Spread (filled after expert returns)

Genuine spread — no contrarian pass needed. Convergence: all five reached
`/all/os/master` as a broadcast term (mute's non-enforced sibling) and "no
dashboard mode" for multi-element; boundary and simplicity independently
produced the same one-sentence law (terms, never composed products) — treated
as signal, not roster overlap, since they reached it from opposite altitudes.
Divergence, the session's value:

- **When master moves:** now (boundary, patch-author) vs manifest-gated
  (protocol, ops) vs deferred entirely (simplicity). Judge ruled
  manifest-gated (`subscribes`), overruling the deferral.
- **Admin verbs on the facilitator:** manifest-promoted by the patch
  (protocol) vs install-level config (patch-author, boundary) vs hardcoded
  single button at most (simplicity) vs reversibility-line (ops). Judge ruled
  install-level allowlist, default empty, reversibility line; Bob arbitrates.
- **What an element is:** reception points inside one instance (boundary) vs
  N same-patch instances with launch identity (patch-author, ops) vs
  sub-selector wire now (protocol) vs build nothing (simplicity). Judge ruled
  the model only (positioned reception point, position-list assign), build
  deferred to S2.

Judgment: `judgment.md` (fable, inline). Fact-check highlights: ops' "breaks
deployed fleet" softened (dashboard not yet adopted on any rig); simplicity's
"principle already ratified" partially held (§1/§4 contradict §3/§6).
