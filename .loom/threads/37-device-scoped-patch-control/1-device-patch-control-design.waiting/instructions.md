# 1-device-patch-control-design

Design device-scoped patch control. Written proposal, **Bob ratifies**, tie
with `decisions.md`; then child implementation stitch(es).

## Ratified so far (Bob, 2026-07-24)

- **Fleet patch = a bulk-set / default over per-node desired patch**, not a
  rival first-class target. Per-node desired patch is the primitive. (Confirms
  advice 1 & 2.)
- **Independent control is NOT gated on being seatless.** Assignment = spatial
  role only; a patch can be switched on any device, assigned or not.
- **Switch/deploy authority lives on the Patch tab** — patch-first: choose a
  patch → choose a target = whole fleet *or* one device, same convergence flow
  at two granularities. The **Device tab** keeps the current-patch display, the
  live control panel, and a **"Set patch…" shortcut** that hands off to the
  Patch-tab action for that device. *(Both the Patch-tab split and the
  "Set patch…" affordance agreed, Bob 2026-07-24.)*

## Test rig for this thread

Two real devices, both on one network in the Dashboard: **Finn Jet** (kite
spool — bopOS-as-one-node-of-a-large-installation case) and **Ciro Toast**
(standalone device). Every per-device behavior here should be exercised across
both; see the `finn-ciro-test-rig` memory.
- **Per-device live control panel on the Device tab** is wanted (advice 4):
  render `dashboard:true` promoted controls scoped to the device's current patch.
- **Engine stop/start on the Device tab is SHELVED** (advice 5). `restart-engine`
  stays; do not add stop/start. Revisit only if Bob raises it again.

## Still to decide

- **Drift semantics:** what it means for a node's desired patch to differ from
  the fleet patch; how it reads on the Device tab and (via 34) the menu bar.
  Settle the fleet-patch definition jointly with
  `feature-backlog/34-fleet-patch-global-state`; coordinate with
  `29-fleet-patch-sync-hang` and `asset-fleet-distribution` — one definition.
- **Patch-tab target picker UX:** how "one device" is chosen alongside the
  existing fleet deploy; confirmation model; reuse the fleet convergence flow
  per-node, don't fork it. Plus the Device-tab "Set patch…" hand-off.
- **Per-device live control panel:** exact rendering (reuse editor param-tree),
  and what shows for offline / unbound / drifted nodes.
- Simulator (`tools/simfleet.py`) parity + Playwright coverage for per-device
  switch, drift display, and the per-device live controls.

## Deliverable

`decisions.md` here; child implementation stitch(es) from the ratified design;
update the parent.
