# automation-3-animated-takeover

Animated automated controls and the take-over gesture, across every surface
that renders promoted `/p/*` controls (All & Groups / Seats live tabs, Seat
detail, facilitator-promoted controls).

Requires `automation-1-engine-and-parity` (generator model) and lands after
`automation-2-show-builder-gui`.

Scope:

- **Local simulation**: the dashboard knows the generator it sent and shares
  the synced clock, so automated controls animate with **zero extra OSC
  traffic** — deterministic for sync LFOs, best-effort for free LFOs and
  mid-flight fades.
- **Take-over**: touching an automated control sends a plain value (§3.2
  last-message-wins) and the animation stops under the finger. Released
  controls stay at the taken-over constant.
- Mixed aggregates (All/Group rows over per-Seat generators) need an honest
  "automated" indication without pretending to a single value — follow the
  existing mixed-value affordance.
- Durable offline/unbound value semantics from thread 12 must survive: an
  automated param's stored full-state value is the catch-up constant, not a
  stale animation frame.
- Verify: house Playwright pattern + simfleet — animation advances without
  wire traffic (assert via outgoing console silence), take-over emits one
  plain value and freezes, replay/catch-up shows the §3.2 values.

The waveform **visualisation** (the "this is automated" waveform rendering)
is NOT this stitch — it is gated behind `automation-4-waveform-ux-gate`.
Use a minimal placeholder indication here if one is needed.
