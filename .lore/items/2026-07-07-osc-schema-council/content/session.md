# Session — bopOS OSC schema council, 2026-07-07

Convened from loom stitch `osc-schema-contract/schema-design-draft` (bopOS loom),
after a framing session with Bob (rulings recorded in ground-truth.md). Deliverable:
**judgment only** — Bob ratifies before the contract draft is written.

## Roster (approved by Bob)

| Seat | Lens | Mandate | Model | Tools |
|---|---|---|---|---|
| expert-protocol-designer | OSC/protocol design craft | Message grammar, addressing, namespaces, discoverability, versioning — a schema any engine or controller can sit on either end of | opus | repo read |
| expert-distributed-systems | Distributed-systems reality check | Discovery, identity, sync, failure modes, UDP broadcast realities at 50–100 nodes; find the constraint that invalidates elegant designs — verify in code | opus | repo read + local network probing if useful |
| expert-platform-agnostic | Platform-agnosticism purist | Design from the office-floor live-image scenario backwards; hunt every hidden Pi/PD/WiFi/I2C assumption in the contract | opus | repo read |
| expert-performer-ux | Performer/artist workflow | Setup and install friction, performance-night stability (Belief System lesson), composer + agent-assisted workflows; how schema choices surface in the dashboard experience | opus | repo read |
| expert-simplicity | Simplicity guard / feature-questioner | Solo maintainer; smallest vocabulary that works; question every proposed message family; migration cost honesty; guard against namespace sprawl and speculative capability machinery | opus | repo read |
| judge | Integrator who verifies | Adjudicate load-bearing facts against the code, name the crux, rule decisively | fable (this session's strongest) | repo read |

## Spread (filled after expert files returned)

Session dropped (usage limit) after all five experts completed, before the judge ran.
Resumed 2026-07-07 (later session): judge ran **inline as the orchestrator (fable)** —
all five designs already in context, so no subagent re-read; strongest model on the
seat that matters, zero duplicated grounding. Experts had run on opus per plan.

**Strong convergence (unforced — lenses were distinct, so treat as signal, not roster
failure):** manifest *file* for patch params (all five; runtime introspection rejected);
`/p/*` patch plane; `/os/*` rename with `/system/*` folded in; **keep all six ports,
reject consolidation and renumbering** (unanimous); capability broadcast rejected as a
subsystem; identity = opaque token with MAC as default value; `bopos.devices` demoted
to optional seed; distribution generalised with a named landing convention.

**Genuine spread (adjudicated in judgment.md):**
1. **Assignment authority** — dashboard-authoritative, node stores nothing
   (distributed-systems) vs node persists own identity (performer-ux) vs soft
   runtime state (platform-agnostic). *The crux.*
2. **Capability carriage** — caps list in hello/heartbeat (dist-sys, performer-ux) vs
   pull-only `/os/report` (protocol-designer) vs manifest+`/os/info` suffices
   (simplicity).
3. **Discovery** — separate `/os/hello` family (dist-sys) vs heartbeat-is-discovery
   (simplicity).
4. **Landing location** — inside patch tree (protocol-designer, simplicity) vs
   framework-owned neutral dir outside the patch git tree (dist-sys).
5. **`/point` timing** — first-class now (protocol-designer, dist-sys: mandatory at
   scale) vs don't mint until needed (simplicity).
6. **Unique adds** — `/os/identify` chirp-to-locate and `/os/mute` panic button
   (performer-ux only); selector/plane grammar (protocol-designer only).
