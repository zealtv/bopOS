# First clean bite — device-scoped patch targeting (proposal)

Bob, 2026-07-24, scoped this as the first slice of thread 37. It deliberately
**excludes** the shared control-surface restructure, the Control-tab rename, the
per-device live-control panel, and preset affordances — those stay in the parent
design. Generator-editing-on-the-surface is **parked to the feature backlog**
(see the parent scope note; not dropped, just not this bite).

## What this bite delivers

1. **A target picker on the Patches page** — first pass: deploy a chosen patch to
   **the whole fleet** *or* **one specific device**. Same convergence flow at two
   granularities; no forked machinery.
2. **A drift badge in the Devices roster** — a device pointed at a patch other
   than the fleet default reads as distinct from `current` / `stale`.
3. **A visible mirror of "the fleet patch"** — recommendation below; it overlaps
   the deferred `34-fleet-patch-global-state`, so its *placement* is a Bob call.

## The load-bearing data-model change

Today `fleet_patch` is a **single global** in `InstallationState`; every device's
`patch_badge` is `patch_badge(device, live_fleet_patch())` — measured against that
one target (`dashboard/server.py:1439`, `state.patch_badge`). There is **no
per-node desired patch**. So "target one device" is not just a UI affordance — it
introduces a **per-node desired-patch override**:

- New optional per-device field, e.g. `device_patch[uid] = {name, fingerprint}`,
  persisted in the durable registry alongside the alias/enabled state (survives
  restart, keyed by exact UID — same discipline as `device_enabled_for`).
- **Effective desired patch for a device = its override if set, else the fleet
  patch.** `public_device` resolves this per device instead of passing the one
  global `desired`. `patch_badge` is then computed against the *effective* target,
  so convergence semantics (`current`/`stale`/`switching`/`failed`) are unchanged —
  they just measure against the right target per node.
- Convergence reuses `converge_fleet_patch` with a **target set of one** (it
  already loops a `targets` set and switches ready nodes together; a singleton
  target set is the whole change). New WS command `set_device_patch`
  `{uid, patch, confirmed}`; deploy-to-fleet stays `set_fleet_patch`. A
  "Clear override / follow fleet" action removes the override so the node tracks
  the fleet default again.

This keeps the parent's ratified framing honest: **the fleet patch is a bulk-set
/ default over per-node desired patch.** Setting the fleet patch writes the
default; a device override is the exception on top of it.

## Drift semantics + roster badge

Two **orthogonal** axes — keep them separate, don't overload one badge:

- **Convergence axis (exists today):** `current / stale / switching / failed /
  missing …` — "is the device *on* its desired target yet?"
- **Targeting axis (new):** is the device pointed at the **fleet default** or at a
  **device-specific override**?

Recommendation: leave the convergence badge exactly as-is, and add a small,
distinct **targeting marker** only when an override is set. Terminology matters:
"drifted" reads as *accidental* divergence, but a per-device target here is
*deliberate*. A UI expert would name deliberate divergence **"pinned"** (or
"custom") and reserve "drifted" for unintended divergence. My recommendation:
**"pinned"** with a pin affordance, tooltip naming the pinned patch + a
"follow fleet" clear. (If you prefer the roster to read `current / stale /
drifted` as one family, we collapse the axes — noted as an open call below.)

## Fleet-patch mirror — UI recommendation

The fleet patch is global state that today only shows on the Patches panel, the
Monitor System card, and per-device diagnostics. "Mirror it somewhere visible"
is, in UI terms, a **persistent status indicator in the global chrome** — the app
header / menu bar — showing the fleet patch name plus a convergence rollup
(e.g. `roomtone · 5/6 current · 1 pinned`), visible from every tab, click-through
to the Patches tab. This is the IDE "git-branch in the status bar" pattern, and
it is **exactly `feature-backlog/34-fleet-patch-global-state`'s menu-bar
indicator**. Recommendation: define drift + the fleet-patch rollup **here**, and
render the menu-bar chip as part of 34 (or pull a minimal read-only chip forward
into this bite if you want it now). Placement is your call — see questions.

## Simulator + tests (part of the deliverable)

- `tools/simfleet.py`: honor a per-node desired-patch override so a targeted
  device converges independently while the rest hold the fleet patch.
- Playwright: per-device deploy from the target picker; roster shows the pinned
  marker on the targeted node and `current` on the rest; "follow fleet" clears it.
- New assertions go into `tests/` by code surface (durable-contract policy),
  not a new tied guard.

## Open calls for Bob (ratification)

- **Targeting terminology:** `pinned` (recommended) vs `drifted` vs collapse into
  the convergence badge family.
- **Fleet-patch mirror placement:** menu-bar chip now (min. read-only) vs defer
  the chip to thread 34 and only land the drift/rollup data here.
- **Persistence:** confirm the per-device override lives in the durable UID
  registry (survives restart), matching enabled/alias discipline.
