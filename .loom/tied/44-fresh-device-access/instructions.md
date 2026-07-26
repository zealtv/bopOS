# 44-fresh-device-access

Make a newly flashed physical device fully accessible from the Devices tab on
the first dashboard session, and make the Dashboard's OSC transport and
shutdown reliable on macOS.

This thread was opened from the live Imani Silver incident on 2026-07-26.
There are two defects:

1. selecting an unbound fresh device crashes the Device-detail render when the
   fleet patch has promoted controls; and
2. the default unbound UDP sender cannot route `255.255.255.255` on this Mac,
   so first-seen requests do not reach the node and Ctrl-C state restoration
   aborts shutdown with errno 49.

See [`diagnosis.md`](diagnosis.md) for the reproduction, live device record,
network probes, relationship between the symptoms, and source anchors.

Both stitches now prescribe their fix (2026-07-26, assessed with Bob): stitch 1
unifies the shared surface's value path through `aggregateValue()` (fix by
deletion — the seat/device special case is an unsafe inlined duplicate);
stitch 2 makes the sender self-locating (bind the discovered LAN source
address, keep the `255.255.255.255` default), adds a transport fault boundary
in `_send_to()`, and makes shutdown exception-safe. Bob also noted fresh
devices onboarded successfully at least three times before this incident —
see the diagnosis's "Prior successful onboardings" section; stitch 2 opens
with a bounded archaeology pass on that.

Children, in order (`1` first — it is UI-only and headlessly testable; `2`'s
hardware adoption check needs Imani Silver online anyway):

- `1-unbound-device-detail` — make selection/detail rendering safe and useful
  before a device is assigned to a Seat.
- `2-macos-osc-routing-shutdown` — make the physical OSC route usable on macOS
  and make send failure unable to abort device processing or shutdown.

## Done when

- An online, unbound, newly discovered physical device can be selected in
  Devices without a browser error and exposes its device administration and
  assignment surface.
- Promoted Device controls preserve the ratified rule: unbound controls are
  visible but disabled; no content control is sent until a Seat binding exists.
- The default laptop launch can send first-seen/report/assignment traffic on
  the active installation LAN without requiring Bob to calculate a subnet
  broadcast address for each session. Explicit target configuration remains
  supported.
- A failed OSC send is observable but does not truncate heartbeat handling,
  leave the device record half-initialized, or prevent application cleanup.
- Ctrl-C reaches a clean application shutdown even when the installation route
  is unavailable.
- Living tests cover both regressions, and Imani Silver is used for the final
  hardware adoption check when available.

Follow `docs/VERIFICATION.md`. Do not edit `.pd` files.
