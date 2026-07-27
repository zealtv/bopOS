# 1-full-manifest-visibility

**Ratified by Bob 2026-07-27** (lore
`2026-07-27-control-panel-ui-and-architecture-braindump`,
`session-directives.md` §3) — this is implementation, not a design gate.

The Control tab must show **all** parameters in a patch's manifest by
default, with value-setting and generator application available on every one.
The manifest's `dashboard:` flag changes meaning: it now defines what appears
on the **facilitator (iPad) view** — the simplified mixing/basic-controls
surface — and no longer restricts the Control tab.

Scope:

- Control tab (and the Device-tab control panel, which shares
  `ControlSurface`): render the full manifest parameter set, not just
  `dashboard: true` params. Preserve nested-address structure.
- Facilitator view: continues to show only `dashboard: true` params —
  confirm this is already its behavior and pin it.
- Simfleet/audition parity and docs: update any prose that says
  "Dashboard live controls come only from `dashboard: true`" (CLAUDE.md,
  README/contract commentary if the flag's meaning is described there).
  If the OSC contract text defines `dashboard:` semantics, this is a
  contract-text amendment — record the delta, keep it additive.
- Verification: headless browser check that a manifest with mixed
  `dashboard:` flags shows everything on Control and only the flagged
  subset on the facilitator page. Durable-surface assertions go in
  `tests/`, per the 27-guard-rot direction.

Keep the change minimal — visibility/routing only, no restyling (that is
`2-control-panel-design`).
