# 11b-single-device-assets-workspace

Waiting only on `11a-device-asset-inventory`. When 11a is tied, claim this and
proceed without a further design gate; the product shape was accepted by Bob
on 2026-07-15 (`.lore/items/2026-07-15-asset-management-direction/`).

Replace the Assets placeholder (`dashboard/static/index.html`, `tab-assets`
panel) with the first operational workflow: manage asset slots on exactly one
online **assigned physical** device at a time.

## Workspace shape

- **Host catalog panel:** list `assets/<slot>/` folders from the existing
  distribution catalog (`dashboard/server.py` `distribution_catalog` already
  supplies name, files, bytes, modified, fingerprint) — show all five,
  fingerprint abbreviated.
- **Target selector:** exactly one device, filtered to online + assigned
  physical devices (the Seats boundary). Offline, unassigned, and simulated
  devices are unselectable with the reason visible. No All/Fleet option.
- **Per-slot state against the selected device**, derived from the 11a
  inventory, never from session receipts:
  - *absent* — host slot not installed on the device → **Send**;
  - *current* — fingerprints match → no action needed;
  - *stale* — installed, fingerprint differs from host → **Update**;
  - *unknown* — inventory unknown (older node, no reply yet) or fingerprint
    still `null` (cache warming) → say so honestly; actions stay available
    but the state label never guesses;
  - *extra* — installed on the device but absent from the host catalog →
    listed beneath the catalog rows, **Remove** only.
- **Send/Update** use the existing manifest-driven `/os/fetch` path (the
  `send_distribution` seam single-target). **Remove** confirm-gates then
  sends `/os/dropassets <slot>` to that one device; extra slots included.
- **Live feedback:** queued/fetching from `/os/fetch-progress`, terminal
  `/os/fetched`, then re-query inventory so the row converges to an observed
  state. After a dashboard restart, state derives from inventory alone.
- **Active-patch warning:** when the selected slot appears in the selected
  device's active patch manifest `slots` (available via the `/os/params`
  data), Update and Remove warn before proceeding: the fetch mutates the
  live directory while the engine runs; the safe migration is sending a new
  side-by-side generation and switching the patch. Warn, don't refuse — and
  do not stop/restart the engine automatically in this stitch.

## Devices tab hand-off

Remove the "Asset send & sync" section from Devices
(`dashboard/static/js/dashboard.js` — the `#distribution` section with
`sync-all`, `distribution-all`, and asset `distributionRow` wiring, roughly
lines 700–770). Devices may keep a compact observed per-device asset summary
that links into Assets, but Assets owns every asset action. Patch
distribution is unaffected.

## Explicitly out of scope

No All/Fleet target, durable fleet desired-assets record, Sync All, rollout
waves, packaging, archives, caches, byte ETA, or automatic engine
coordination — that is `asset-fleet-distribution`. No free-space display
(11a's seam carries none). Staged activation is
`asset-fleet-distribution/fleet-1-node-staged-slot-swap`, not this stitch.

## Verification

Ship a real-dashboard + simfleet Playwright verifier (copy the newest tied
`verify_*.py` template; `~/.venvs/bopos` venv, non-default ports, repo by
marker, teardown) covering: send, update, and remove flows converging to
observed states; extra-slot removal; single-target isolation (only the
selected device receives the fetch); offline/unassigned/simulated guarding;
active-patch warning copy on Update and Remove; restart-derived observation
(reload → states from inventory, not receipts); absence of fleet-wide asset
controls in Assets; absence of the asset section in Devices. Mind the three
Playwright gotchas in CLAUDE.md. Retain reviewed screenshots and results in
the stitch directory.
