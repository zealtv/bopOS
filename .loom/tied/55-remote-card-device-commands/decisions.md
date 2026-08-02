# Decisions

Bob clarified on 2026-08-03 that Remote device commands are targetable rather
than global.

1. Every derived Remote target card owns its command controls: All, group, and
   Seat cards all expose the venue-enabled command allowlist.
2. A card action uses the card's ordinary selector: `all`, `gN`, or the Seat
   ID. The removed Fleet setup strip is not a second command surface.
3. Desktop Device Actions retain exact-UID delivery. That administrative path
   remains distinct from Remote's venue-selector targeting.
4. Existing safety behavior remains: restart engine and update bopOS execute
   after confirmation; reboot and shutdown require the destructive hold.

This supersedes the Remote-placement interpretation recorded in stitch 54.
