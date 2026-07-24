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

## Scope widened 2026-07-24 (Bob-confirmed): the shared control surface

Bob's braindump — lore item `2026-07-24-patching-session-braindump` —
generalizes this thread's per-device control panel, and Bob confirmed the
widened scope same day: this design session also owns the **reusable
control-surface component** and its three hosts. The proposal should cover:

- **One control-surface component**, manifest-driven, rendered in three
  contexts: the **patch editor** (drives the patch being edited, live), the
  **Device tab** (this thread's per-device panel — an instance, not a
  one-off), and a **Control tab** — the Dashboard tab renamed — where a
  target filter (all / groups / specific seats) selects what the surface
  addresses, alongside cues, master control, and presets.
- **The IA lesson behind it:** as patches grow parameters, the Seats-tab
  per-seat grid detail runs out of vertical room and the cue section crowds
  out the parameters, which should be the focus ("that whole cue section is
  much too big — maybe off to the side"). Targeting should be a filter on
  one view, not navigation to different views; the per-seat grid "perhaps
  isn't the best approach." Fold the cue-section-size complaint into this
  restructure rather than patching it separately.
- **Dashboard → Control rename**: settle it here; it also touches the
  parked `dashboard-terminology-review` thread — one owner, note the
  ruling there.

**Generator editing on the surface (Bob, 2026-07-24, same conversation):**
each param control on the shared surface should offer generator editing —
choose an LFO, set rate/depth etc. from the interface, not only via the
Show inspector's message builder. The `automation-2` generator builder GUI
already compiles to the §3.2 wire grammar; extract/reuse it as part of the
component rather than duplicating it. (What generators mean *inside a
preset* — capture and mix-interpolation — is thread 41's design, but the
surface must host the per-param generator affordance.)

Presets themselves are **thread `41-preset-primitive`** (Bob-gated design:
manifest-scoped presets, save-from-editor, load per seat/group/all,
Show-tab triggering with optional interpolation). This design only needs to
leave room on the surface for save/load-preset affordances; `41` designs
what a preset *is*. Precision float entry is thread
`40-precision-param-input` (workable, ungated) — the shared surface should
assume typed-entry-capable controls.
