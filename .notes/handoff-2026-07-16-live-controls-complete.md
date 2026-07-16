# Handoff — Dashboard live controls complete (2026-07-16)

This supersedes `.notes/handoff-2026-07-16-alias-complete-updater-gate.md`.

## Completed

- Promoted parameters are now Seat-owned All, Group, and Seat cards sourced
  fail-closed from the staged host manifest. Nested paths remain qualified on
  the wire and in durable Seat state.
- All/Group mixed aggregates, offline/unbound Seat controls, and compact All and
  per-Seat **Send all** replay are complete. All replay expands through numeric
  Seat selectors in stable order; Group replay is intentionally absent.
- Physical-device mute uses the ratified exact-UID command and receipt. Desired
  mute persists both in the node store and host-global device registry. Fleet
  safety mute is a separate session overlay, and effective mute is their OR.
- Selected Device detail has Mute/Unmute; Devices roster rows expose accessible
  device/fleet/pending/unconfirmed mute indication. Forget deletes mute intent.
- Real helper, dashboard, simulator, audition rig, and OSC contract are aligned.

Focused verification passed **20/20 backend**, **13/13 protocol**, and **16/16
browser/touch** checks. Adjacent parameter regressions passed **41/41**; alias
registry **16/16**, group protocol **37 checks**, and asset inventory **27/27**
also passed. No `.pd` file changed. Real Pi mixer/engine fallback, installation
LAN, audible output, Safari/iPad hardware, and screen reader remain untested.

## Next

Claim `ui-tabs/tabs-3-next-sweep/13-diagnostic-density` and complete the already
ratified polish sweep:

- subtle host Git shorthand beside the bopOS wordmark;
- remove the listed extraneous interface copy;
- place desired fingerprint directly above reported content identity;
- add Seats inspector dividers between Seat workspace, Elements, Groups,
  Physical device, and Venue;
- cap new UI element authoring at two without truncating existing larger data;
- show the bound device IP in Seat Physical device detail while keeping hostname
  and UID exclusive to selected Device detail.

The manually running dashboard process on port 8080 predates Live Controls and
must be restarted before Bob evaluates the new UI or protocol behavior.
