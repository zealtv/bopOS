# 05-compact-chrome

Apply the ratified chrome density pass: sharper corners, buttons that wrap
tightly around their text, bounded scroll regions, and general compaction. `01` is paused, so settle
scope (Show-tab-only first vs app-wide) and the concrete values with Bob in
this stitch before applying; the facilitator tab is excluded either way
until separately reviewed.

## Outcome

- Use the concrete values from the ratified review (radius, padding,
  heights) expressed through the existing CSS variable/theme system — one
  place to change, both themes covered. No hard-coded one-off values
  scattered per-component.
- The step list is a bounded scroll region (it already scrolls via the
  `p4` scrollbox — verify the bound reads clearly with the new chrome and
  the edit bar stays pinned).
- Density must not shrink effective hit targets below touch size on
  controls that remain touch-relevant; keyboard focus visibility is
  retained everywhere the chrome changes.
- If app-wide scope was ratified: apply tab-by-tab in one sweep guarded by
  the shared variables, and check the Devices/Seats/Patches/Assets tabs for
  layout breakage; the facilitator page is untouched.

## Verification

Focused Playwright: assert the ratified radius/padding values on
representative controls; edit-bar pinning and bounded list scroll; hit
target sizes at 768px; light/dark screenshots of the Show tab (and each
affected tab if app-wide) at 1280px and 768px; no horizontal overflow.
Re-run the tied edit-bar, OSC-terminal, and compact-row suites unmodified.
Retain screenshots.
