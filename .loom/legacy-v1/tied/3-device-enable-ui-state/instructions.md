# 3-device-enable-ui-state

Present the physical control consistently as Device enabled/disabled.

- Replace Mute/Unmute wording, indicators, accessibility labels, and public
  Dashboard state with positive Device enabled/disabled terminology.
- Update Dashboard, node, simulator, audition, OSC contract/reference docs, and
  focused protocol checks to the ratified `enabled` request/receipt/report
  vocabulary.
- Keep MUTE ALL visually and semantically distinct as an execution control.
- Migrate durable host/node state according to the ratified design; with Finn
  Jet as the only deployed device, do not retain confusing compatibility
  vocabulary without a concrete need.
- Keep pending/current/unconfirmed feedback based on physical-device
  acknowledgement.
- Confirm every Devices-tab action continues to name and target a physical UID
  while Simulation or Patch Edit is active.

Do not edit `.pd` files.
