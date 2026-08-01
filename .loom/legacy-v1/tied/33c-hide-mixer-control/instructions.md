# 33c-hide-mixer-control

Bob, 2026-07-23: mixer control is an implementation/hardware concern and should
not be operator-editable in the Device Audio interface.

- Remove the mixer-control select and rebalance the four remaining controls.
- Preserve the existing mixer value when applying changes to the same card,
  provided that value is still enumerated.
- When the sound card changes, or the stored control is no longer available,
  send `mixer_control: null` so node-side Auto discovery owns the choice.
- Keep the v1.11 wire/report field and node configuration support; this is a UI
  ownership correction, not a protocol migration.
- Update the focused browser journey to prove the control is absent and normal
  same-card edits do not silently change the stored mixer value.
