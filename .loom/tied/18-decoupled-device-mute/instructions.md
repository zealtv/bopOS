# 18-decoupled-device-mute

Apply Bob's 2026-07-16 hands-on revision to the ratified two-layer mute model:

- Persistent exact-device mute and session fleet safety mute are independent
  controls with effective node mute remaining their logical OR.
- Keep the selected Device Mute/Unmute action available while fleet mute is on,
  so an operator can establish the state that will remain after fleet release.
- Make the Devices roster indicator specific to persistent device mute only;
  fleet overlay state belongs to the global fleet control and must not recolour
  or slash every physical-device indicator.
- Keep acknowledgement/pending honesty and old-node behavior intact.
- Verify: fleet on → device mute on → fleet off leaves that device muted; fleet
  on → device mute off changes persistent state while effective mute stays on.

This supersedes only the old proposal's UI ruling that disabled Device controls
during fleet safety and made roster indicators reflect effective/fleet mute.
The exact-UID wire contract and two-layer OR semantics remain unchanged.
