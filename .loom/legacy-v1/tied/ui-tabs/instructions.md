# ui-tabs

**Goal:** restructure the dashboard's single-page tech view into tabs, decided
2026-07-14 with Bob. The working tab map, to be refined by tabs-0:

- **Overview** — fleet status, device selection, health/convergence summaries.
- **Spatial** — the map: elements, points, listener puck.
- **Fleet management** — the operational verbs: reboot/update all, patch
  distribution and switching, asset sync.
- **Patch editor** — the composer-helper mode (built by the `patch-editor`
  thread; this thread only reserves its tab).

Also in scope: tidy the facilitator/technical view switch (currently
facilitator button left, technical right — inconsistent placement when moving
between views).

Process ratified by Bob 2026-07-14: **paper IA first, hands-on review after** —
tabs-0 produces a written tab map Bob ratifies, tabs-1 builds the skeleton,
tabs-2 is the interactive review session inside the real tabs. Don't run ahead
of the tabs-0 gate.

Ordering: after `fleet-patch` — the fleet-patch design defines much of what
Overview vs Fleet management contain (global patch selector, badges, which
per-device controls disappear). Before `patch-workflow-friction` — the
composer docs must describe the final tabbed UI.
