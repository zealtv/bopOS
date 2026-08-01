# fp-3-fleet-ui

The fleet-patch dashboard surface, per ratified fp-0 §4. Needs fp-2 tied.

- Global control area: fleet patch selector + **Set fleet patch** (single
  confirmed action) + convergence summary ("7 current · 1 switching · 1
  stale") + Revert.
- Device rows: compact observed-state badge; exceptional rows draw
  attention without duplicating the global selector.
- Remove per-device patch dropdown, Switch, and per-device Send Patch from
  the ordinary interface. Device detail keeps diagnostics (listing, fetch
  states, reported fingerprint) and remediation: retry (missing/stale),
  re-switch (mismatch), Pull latest for git-managed (◆) patches. Nothing
  should imply heterogeneous patches are a supported composition model.
- Asset Send/Sync untouched.
- Coordinate with `ui-tabs`: if tabs-1 has landed, this content belongs in
  the Fleet management / Overview split the ratified tab map defines; if
  not, build in the current layout and let tabs-1 rehome it.
- Playwright verify against simfleet: selector drives the fleet, badges
  render each state (including induced stale), per-device patch controls
  absent from ordinary view, revert flow.
