# Session — engine-boundary council, 2026-07-11

Design-only council per `~/repos/ai-kit/skills/council-design-session/SKILL.md`,
convened from the `engine-boundary-council` loom stitch. Problem seed:
`.loom/threads/engine-boundary-design/instructions.md` (the goal thread's nine
questions) + `.notes/pd-engine-boundary-design-brief.md` + lore
`2026-07-11-pd-engine-boundary-brain-dump`. All artifacts live in this stitch
directory. No code, `.pd` files, or contract edits from this session.

## Roster

Five independent experts, launched in parallel, forbidden from reading each
other's files. Experts run on **opus** (one tier down); the judge runs on
**fable** (strongest available). All experts have full repo read access.

| seat | file | lens & one-line mandate |
|---|---|---|
| engine-api | `expert-engine-api.md` | Patch-author ergonomics: define the one abstraction a PD/SC/oF author holds in their head; equivalent surfaces across engines. |
| transport | `expert-transport.md` | UDP/process topology: who binds what, throughput and packet-rate budgets, meters and IO streams, production vs audition sockets. |
| operations | `expert-operations.md` | Rig reality: mute safety, boot/runtime failure modes, migration of deployed fleets, what breaks at 3am mid-show. |
| creative-tools | `expert-creative-tools.md` | Composition UX: dashboard feedback, diagnostics, naming as creative vocabulary, the report-on-request framing. |
| simplifier | `expert-simplifier.md` | Challenge existence: should the PD↔helper forward, the port fan, and the abstractions exist at all; find the smallest coherent model. |

Contingency: if the five summaries converge without a real crux, one contrarian
seat is added before the judge (per the skill). **Exercised:** the five seats
converged on the headline, so `expert-contrarian.md` (opus, the one seat
allowed to read the others) was briefed explicitly against the consensus.
Judge: fable, `judgment.md`.

## Reflection

- The contrarian seat earned its cost: every attack cited real code, two
  reshaped the ruling (alias-first ordering; one-shot-first probe), and the
  judge called it "the best-evidenced seat at the table". When a roster
  converges this hard, the contrarian is where the verification pressure
  comes from — keep the pattern.
- Operations found the single migration-reordering fact (`/helper/*` handled
  only via the PD forward) that three cleaner designs would have silently
  broken — the reality-check seat justified itself exactly as the skill
  predicts.
- Ground-truth.md decoding the PD wiring (object-index connect lists →
  described signal flow) was load-bearing: seats could verify rather than
  re-derive, and no design inherited a wiring error.
- Bob's mid-session note (the bopos.py rename) arrived after launch and was
  routed to the judge via this file + the judge brief — session.md as the
  live coordination surface worked.

## Spread (recorded after expert return)

**Convergence (near-unanimous, all five seats):** one process owns LAN 6660
per device (helper, generalizing the seam-5 relay and `tools/audition.py`);
PD stops binding the LAN and joins SC on the identical selector-stripped
localhost 6661 surface; the PD→7770 admin forward dies; continuous meters are
deleted (Bob's pre-blessing taken); the `/rpt`/echo/PX-PY tangle is replaced
by a demand-driven, unicast, TTL/lease-bounded report-on-request facility;
buses get a coherent bopos-prefixed direction/plane vocabulary.

**Genuine cruxes (secondary but load-bearing):**
1. **Run-context delivery** — engine-api wants an OSC `/config`-style pull;
   operations vetoes OSC-at-boot as a race and keeps launch file/env transport
   with helper as *owner*.
2. **Migration order** — simplifier's first step is pure deletion of the 7770
   admin path; operations found `/helper/*` legacy verbs are handled *only*
   via the PD forward today, so an alias inside helper's 6660 listener must
   land first or deployed-rig reboots die silently.
3. **io ports** — transport keeps the 6662/8880 pair as a measured performance
   boundary; simplifier deletes 6662 and folds io delivery into the one engine
   ingress port.
4. **Probe/report shape** — creative-tools wants a leased-stream `/os/probe`
   (one verb, optional time-boxed stream); transport/simplifier want a
   narrower TTL'd tap; operations demands unicast + deadman.

**Bob's mid-session note (2026-07-11):** the emerging consensus (helper as the
sole LAN citizen) reads as validation of his brain-dump impulse to rename
`helper.py` → `bopos.py`. The judge is explicitly instructed to rule on
process naming — the brief's own condition ("a rename alone does not repair
the boundary; rename only alongside a clarified role") now has its clarified
role on the table.

**Remedy for the headline convergence:** no seat challenged making helper a
hot-path dependency for *all* engine control (today PD's master/`/p/*` bypass
helper entirely; the relay makes helper death mean loss of control, not just
loss of admin). Per the skill, one contrarian seat (opus,
`expert-contrarian.md`) is briefed explicitly against the consensus before the
judge.
