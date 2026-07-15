# Initial code diagnosis of tabs-2 observations

Read-only diagnosis; no fixes implemented in this review stitch yet.

- **Live / Simulate / Edit is accurate.** `Dashboard.set_supervisor_mode`
  accepts exactly `off | simulate | edit`; `off` is the implementation spelling
  for Live. Simulate and Edit already stop each other before launch.
- **Redundant Simulate action:** `renderSimulation` creates `#edit-sim-patch`,
  while Patches independently owns editor launch. It is safe to remove the
  cross-link from Seats.
- **Stale cards after stopping simulation:** the server clears virtual devices
  and broadcasts full state, but queued `device_update` broadcasts for a removed
  audition uid are still sent because `broadcast()` only enriches a device
  update when the uid remains in state; otherwise it sends the stale payload.
  Both clients then blindly merge that uid back into their local device maps.
  This explains why refresh (a fresh full state) clears the cards.
- **Hostname leaking into seat name:** intentional current code in
  `bindDeviceToSeat()` renames a default `Seat N` to `device.hostname` before
  binding. The new review rejects that coupling; remove the auto-rename.
- **Dashboard MAC labels:** the standalone Dashboard card renders
  `d.name || d.uid`, but runtime device records deliberately carry no seat name.
  The client must resolve the bound seat and label the card from seat name/ID.
- **Preset target:** yes. Presets persist `seats.<seat-id>.<param>` plus master;
  load applies values to the durable seat and sends them to its currently bound
  device. Seat is the correct live-control identity.
- **Seat controls in Devices:** `renderDetail()` constructs identity, Seat,
  Position, Params, Patch diagnostics, Asset sync, Actions and Report in one
  mixed panel. Tabs-1 moved that indivisible panel to Devices, exposing the old
  model leak. It now needs separation rather than another move wholesale.
- **Seat ID cannot change:** the UI disables the ID input and `update_seat`
  updates only name/positions/patch/params under the existing ID-keyed record.
  A real atomic reindex operation is required in Seats.
- **Unbound device limitations:** the unbound branch of `renderDetail()` shows
  identity/bind/forget/Identify plus patch diagnostics, but omits framework
  actions, report refresh and any bring-to-fleet action. The backend selector
  is seat-derived, so most OSC commands currently cannot target an unbound
  node by numeric selector. Identify is the exception because it targets uid.
- **Duplicate device listing:** tabs-1 deliberately renders every real device
  in active/recent plus unbound devices again in a second list. This is not a
  data duplication bug, but the review can reject the presentation.
- **Stuck `switching`:** patch badge precedence treats any `patch_switch` value
  as switching. That field clears only on an attributable `/os/rev`; the
  fallback refresh merely requests patches/params/report after eight seconds.
  A missing or unattributable UDP receipt can therefore leave `switching`
  indefinitely even if the observed patch listing has converged. The state
  machine needs bounded reconciliation/failure semantics.
- **Fleet patch location:** current desired-state mutation is in Devices, but
  the operation already stages one host catalog patch and then converges it.
  Moving desired-patch selection/Set/Revert to Patches is consistent with
  choosing content there; Devices should retain observed badges, diagnostics
  and one-click repair to the chosen desired state.
- **Fingerprint density:** full fingerprints are rendered directly in both the
  detail list and table. A shortened tail plus copy affordance is presentation
  only; preserve the full string in title/data/clipboard.
