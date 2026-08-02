# 55-remote-card-device-commands

Correction from Bob, 2026-08-03: Remote framework commands belong on **each
target card**. They are selector-targeted commands, not one global command
strip.

- Delete the standalone `Fleet setup` command row.
- Render the venue-enabled commands on every Remote All/group/Seat card.
- Send the card target as `all`, `gN`, or Seat ID through the ordinary
  selector-addressed `/os/*` path.
- Preserve exact-UID actions on the desktop Devices surface; those are a
  different administrative targeting path.
- Keep the venue allowlist editor and destructive hold behavior.
