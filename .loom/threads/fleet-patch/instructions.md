# fleet-patch

**Goal:** the fleet runs one desired patch, and the system makes convergence to
it observable and operable — one fleet-level patch selection, per-device
observed state (`current`, `switching`, `missing`, `mismatch`, `stale`,
`unknown/offline`), and reliable drift detection by patch *content identity*,
not just name.

Framing and constraints live in
`.notes/handoff-2026-07-14-fleetwide-patch-next.md` (2026-07-14). Key rules:

- Design before implementation — do **not** start by building per-device patch
  selection. fp-0 produces the proposal; Bob ratifies before any children are
  implemented.
- Any wire addition must be additive to contract v1.3 and mirrored in simfleet
  and managed audition in the same stitch.
- Heterogeneous per-device patches remain an explicit future bridge, not latent
  complexity in today's state model or UI.

This goal's UI conclusions (global fleet patch selector, sidebar badges,
removal of per-device patch dropdowns from the ordinary interface) feed the
`ui-tabs` thread — its IA proposal consumes fp-0's ratified output, so this
thread is first in the cross-thread queue (see CLAUDE.md).

Ties when the ratified model is implemented: one durable desired patch in
installation state, convergence badges in the dashboard, content-identity
drift detection working against simfleet and bop000.
