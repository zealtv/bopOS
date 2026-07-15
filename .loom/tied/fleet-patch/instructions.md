# fleet-patch

**Goal:** the fleet runs one desired patch, and the system makes convergence to
it observable and operable — one fleet-level patch selection, per-device
observed state (`current`, `switching`, `missing`, `mismatch`, `stale`,
`unknown/offline`), and reliable drift detection by patch *content identity*,
not just name.

Framing and constraints live in
`.notes/handoff-2026-07-14-fleetwide-patch-next.md` (2026-07-14). Key rules:

- **Design ratified 2026-07-14** — fp-0 tied; the record is
  `.lore/items/2026-07-14-fleet-patch-design-ratified/` (also in the tied
  stitch). Bob's Q1–Q4: seat `patch` field deleted; Set fleet patch is one
  confirmed converge-then-switch action; stale retry is operator-triggered;
  the fingerprint amendment folds into v1.4 with pe-1's cues.
- Work fp-1..3 in numeric order; fp-4 is the hardware gate (waiting).
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
