# Handoff — loom tidy and stale-item audit (2026-07-26)

Bob reviewed the parked loom and changed its shape.

## Changes

- Dropped `18-show-chrome-density`. Its completed Show work remains in tied
  history. A new `desktop-ui-overhaul/01-density-and-layout-design` loose end
  carries the wanted direction: smaller controls, tighter padding and gaps,
  clearer desktop hierarchy, and less wasted space across the app.
- Dropped `dashboard-terminology-review`: thread 37 already ratified and
  shipped the user-facing **Control** name. The manifest's `dashboard: true`
  field and `#dashboard` tab alias remain compatibility surfaces.
- Dropped `20-console-dock/07-map-tab` and tied the completed Monitor parent.
  A map can return once hands-on sequencing work supplies a concrete need.
- Created `fleet-testing` and moved `asset-fleet-distribution`, `clock-sync`,
  and `spatial-audio` beneath it. Their existing waiting leaves and acceptance
  boundaries are unchanged.
- Audited `framework-version-management`: it is only partly stale. Update
  actions, receipts, reboot/reappearance behavior, raw revisions, and a real
  persistent-node gate have shipped; desired-state comparison and honest
  current/stale/unknown/diverged classification have not. The thread was kept,
  and its brief now covers only that remaining gap.

## Live next action

`desktop-ui-overhaul/01-density-and-layout-design` is the only new loose end.
The refreshed framework-currentness design returns to `.waiting` for Bob after
this intake edit.
