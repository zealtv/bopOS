# 37-device-scoped-patch-control

Let an operator target a patch to (and interact with) a single device
independently of the fleet.

Motivating case (Bob, 2026-07-24): two devices on one network in the
Dashboard — **Finn Jet** (a kite spool, exercising bopOS as one node in a
large installation) and **Ciro Toast** (a standalone device being set up to
run on its own). Both must be switchable and controllable per-device without
pushing to the whole fleet, and without standing up a second bopOS instance.

Hard constraint: **do not run a second bopOS instance for the second patch.**
`bopos.py` alone owns LAN 6660/5550 (discovery/heartbeat/command); a second
dashboard would contend for those ports and for node discovery. Per-device
control has to live inside the one Dashboard.

## Advice already given (starting position, not ratified)

- **Per-node desired patch is already the primitive.** Fleet-patch convergence
  works by setting every assigned node's desired patch + restarting its engine
  (`dashboard/static/js/dashboard.js:481`). "Target a patch to one device" =
  set that one node's desired patch without touching the others; the
  fingerprint/convergence machinery is already per-node.
- **Frame the fleet patch as a bulk-set / default, not a rival target.** A node
  whose desired patch differs from the fleet patch is *drifted* — the exact
  state `feature-backlog/34-fleet-patch-global-state` wants to show in the menu
  bar. **Define "the fleet patch" once, here and in 34 together**, or it gets
  defined twice.
- **Do not gate independent control on being seatless.** Assignment = spatial
  role; it should not decide whether a patch can be switched. Unassigned
  devices (Ciro Toast) benefit, but so does a one-off tweak to an assigned node.
- **Per-patch control panel on the Device tab:** reuse the `dashboard:true`
  manifest-driven promoted-control rendering (today All/Group/Seat), scoped to
  one device's current patch — reuse the editor param-tree renderer.
- ~~**Engine stop/start from the Device tab.**~~ **Shelved** (Bob, 2026-07-24);
  `restart-engine` stays. Revisit only if it comes up again.

Bob's 2026-07-24 rulings on this advice are recorded at the top of
`1-device-patch-control-design`; the switch/deploy surface is the Patch tab
with a Device-tab shortcut and live-control panel.

## This is a Bob-gated design (user-facing Dashboard IA)

Produce a written proposal, mark `.waiting`, surface to Bob; do not implement
past the ratified design. Design stitch: `1-device-patch-control-design`.

## First bite ratified + design stitch tied (Bob, 2026-07-24)

The **first clean bite** was scoped and ratified: per-node desired-patch
override (durable UID registry) + Patches-tab target picker (fleet *or* one
device, reusing `converge_fleet_patch` with a singleton target set) + a
roster **"pinned"** marker (separate axis from the convergence badge) +
fleet-patch drift/rollup **data** (the visible menu-bar chip stays deferred to
`feature-backlog/34`). Design stitch `1-device-patch-control-design` is **tied**
(`decisions.md`, `proposal-first-bite.md`). Implementation is the loose end
`2-device-patch-targeting`.

**Still open in this parent** (not the first bite): the shared control-surface
component, Control-tab rename, per-device live-control panel, "Set patch…"
Device-tab hand-off. **Generator editing parked** to
`feature-backlog/38-generator-editing-on-surface`.
