# 13-diagnostic-density

Reduce operational diagnostic density: show only fingerprint/content-identity
tail (8–12 chars), click to copy full value with feedback, and clarify target
counts/progress/action outcomes. Retain full values in accessible title/data.

Place the dashboard host checkout shorthand subtly beside the `bopOS`
wordmark. This is the sufficient framework version indication for now and does
not reopen the parked framework-version-management design.

Remove the following extraneous interface copy without replacing it with new
help text:

- the device-alias two-word/Seat/hostname explanation;
- the selected Device explanation of what lives in Seats;
- the listener-drag, heading, Seat-dot and point-field paragraph;
- the Fleet patch production-choice sentence and `desired fleet patch` label;
- the audition-runtime launch sentence;
- the manifest dashboard-declarations/audio-patch sentence;
- both single-device Assets scope/exactly-one-target paragraphs.

In Patch diagnostics, put **Desired fingerprint** immediately above
**Reported content identity** so their values can be compared vertically.
Keep this pass terse: do not introduce replacement explanatory copy while
implementing these changes.

Refine the Seats inspector without adding help prose:

- add clear visual dividers between Seat workspace, Elements, Groups,
  Physical device, and Venue;
- cap element authoring at two in the UI. Disable further Add actions at two,
  but do not narrow the protocol, truncate loaded data, or reject a future/
  legacy Seat that already contains more positions;
- show the bound physical device's IP address in the Physical device section
  so an operator can identify the SSH target. Keep hostname and UID/MAC
  exclusive to selected Device detail.

Fold in the 2026-07-16 live-surface follow-up:

- remove the stray `Seat presets` label when there are no preset controls;
- have a UX-focused reviewer assess the whole Dashboard and recommend how to
  distinguish aggregate controls (All Seats and Groups) from individual Seat
  cards, explicitly comparing tabs with lighter visual grouping before the UI
  treatment is chosen.

Master and fleet mute replay from **Send all** was considered and explicitly
held pending hands-on use. Keep the current parameter-only semantics for both
All Seats and per-Seat replay.
