# Results — single-device Assets workspace

## Outcome

- Replaced the Assets placeholder with an operational host-catalog versus
  one-device workspace.
- Only online, assigned physical devices are eligible; offline, unassigned,
  and simulated devices remain visible with reasons but cannot be targeted.
- Host rows show name, files, bytes, modified time, abbreviated fingerprint,
  and inventory-derived absent/current/stale/unknown state. Device-only slots
  appear separately as extras.
- Send, Update, and extra-slot Remove converge through the existing fetch/drop
  paths and fresh `/os/assets` observations. Session receipts provide live
  queued/fetching/failure feedback but never manufacture current state.
- Active-patch declarations now retain `active_asset_slots`; Update and Remove
  warn about live in-place mutation while allowing the operator to continue.
- Removed fleet asset controls from Devices, leaving a compact observed summary
  and link into Assets. Patch distribution remains unchanged.
- Backend enforcement rejects fleet, offline, unassigned, and virtual asset
  mutations even if a client forges a WebSocket message. Safe visible asset
  slot names are consistent across catalog, URLs, node fetch/drop, and simfleet.
- Repository ignore rules exclude every asset slot and cache artifact while
  retaining `assets/README.md`, which documents slot layout, deployment,
  side-by-side revisions, live-update risk, naming, and the Git boundary.

## Verification

- Focused real-dashboard + three-device simfleet Playwright verifier:
  **17/17 passed**, with zero page errors.
- Covered catalog facts, target guards, absence of fleet controls, Send live
  phases and observed convergence, selected-device isolation, forged target
  rejection, extra Remove, active Update/Remove warnings, dashboard restart
  recovery from inventory without receipts, Devices hand-off, and a 390px
  touch-sized/no-overflow layout.
- Retained and visually reviewed `01-assets-workspace.png` and
  `02-assets-narrow.png`; hierarchy, state/action distinction, and responsive
  stacking are clear.
- Assets 11a regression: **27/27 passed** after the 11b integration changes.
- Patches fleet workflow browser regression: **10/10 passed**.
- Group dashboard state/bridge suite: **6/6 passed**.
- Python compilation, JavaScript syntax, and `git diff --check` passed.
- `git check-ignore` confirms example slot content is ignored and the Assets
  README is explicitly retained.
- The older Devices browser verifier passes its first eight checks, then times
  out on its hard-coded contract-version `1.5` assertion; v1.6 is the intended
  11a result. Other retained stale-verifier caveats remain recorded in the 11a
  results.

## Unexercised surfaces

`bop000`, the installation LAN, physical iPad, audio engine, audible rig, and
large real asset transfers were not exercised. No `.pd` file changed.
