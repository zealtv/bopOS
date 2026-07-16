# 14-declared-cue-triggers

Add the active fleet patch's declared cues to the live Dashboard as clear,
touch-friendly triggers. Run placement and hierarchy past a UX/UI reviewer
before implementation, considering the whole Dashboard rather than the cue
panel in isolation.

- Render label and optional description from the desired fleet patch manifest;
  retain the cue ID as the wire identity and accessible context.
- Fire through the existing synchronized `fire_cue` path and shared lead-time
  control; do not add a second scheduler or change the OSC contract.
- Define honest empty, unavailable, and many-cue states without adding help
  prose that competes with live controls.
- Decide whether the free-text cue control remains and make declared cues the
  primary path.
- Remove the idle "scheduled against the shared clock" text; only show status
  after an actual cue action.
- Verify against the real dashboard, host catalog, simfleet, and touch-sized
  Chromium. Cover cue rendering, exact ID delivery, scheduling feedback, and
  relevant responsive/accessibility behavior.
- Do not edit `.pd` files.
