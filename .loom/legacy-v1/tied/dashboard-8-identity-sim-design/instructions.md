# dashboard-8-identity-sim-design

**2026-07-13: proposal written — `.waiting` on Bob's ratification.**
Deliverable kept in lore: `.lore/items/2026-07-13-seats-identity-sim-proposal`
(same text as `proposal.md` here; code surveys with file:line evidence in
`survey-identity-state.md` / `survey-simfleet-audition.md`). Core: split
installation.json into **seats** (durable places in the piece) and
**devices** (heartbeating boxes); binding fires the existing `/os/assign`;
Simulate toggle = dashboard-managed audition rig inhabiting unoccupied
seats with ephemeral virtual rows; puck sim-only; forget + bulk-forget; one
additive wire change (hostname in `/os/report`). Six open questions Q1–Q6
(first: the noun). On ratification: create `d8-1..3` children per proposal
§8 (deferred like dist-1..4 unless Bob says go).

Design proposal (decision gate — Bob ratifies): the device-identity data model
and dashboard-managed simulation. Source: Bob's 2026-07-13 brain dump
(`.lore/items/2026-07-13-composer-experience-brain-dump`) — read it first;
this is the "serious UX design consideration" item.

The core problem: a composer wants to **pre-arrange the space** — designate
positions and IDs before any hardware exists — and later bind those
positions/IDs to real devices, cleanly and reliably, both locally and when
deploying. That needs an explicit model of *device-as-representation in
bopOS* vs *real device*, and how the mapping happens. The composer is usually
also the person deploying.

Feeding into the same model:

- [ ] **Simulation from the dashboard:** Bob's later refinement — a single
      simulate on/off toggle that simulates **all nodes on the space**; each
      node is either the position of a real bopOS device or an optionally
      virtual device. (Earlier sketch: a "simulate" sidebar section with
      add/remove devices — the toggle-over-all-positions model superseded it,
      but adding/removing virtual devices still needs a home.) Sim devices
      accept patch sends just like real ones. Saving sim-fleet state should
      fall out of the identity model, not be a separate mechanism.
- [ ] **Forget device:** discovered UIDs currently persist in
      `installation.json` forever; forgetting sims required a hand-rolled jq
      surgery (recorded verbatim in the lore item). The model needs a
      first-class forget/retire.
- [ ] **Listener puck** is only visible when simulation is active — its
      visibility hangs off the simulate toggle.
- [ ] Reconcile with what exists: `tools/simfleet.py` (external process,
      real OSC), the audition rig instances, `installation.json`
      device/position schema, discovery/assign (dashboard-3, tied), and
      hostname-derived naming (ui-0 lands the suggestion; the model should
      make it coherent).

Deliverable: a written proposal in `.lore/` covering the data model
(positions/IDs as first-class, device binding, virtual devices, forget),
the simulate toggle UX, and migration of `installation.json`. Then mark
`.waiting` and surface to Bob. No implementation past the unratified design.
