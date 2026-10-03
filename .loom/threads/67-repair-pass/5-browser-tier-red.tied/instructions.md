# 5-browser-tier-red

**Status:** verified complete — full browser tier green after preset removal
**Goal:** `tools/run-tests.sh browser` is green again, and every failure is
either fixed or explained.

## Current outcome

The full tier now passes all 23 living journeys; see `closeout.md` and
`closeout-browser.log`. Preset-only journeys were retired with their feature
in `2-remove-presets`. Earlier repair evidence remains in `verification.md`
and `browser.log`. This close-out also corrects a detached-row CSS read in the
Show generator test while preserving its exact grid-width assertion.

## Initial failures (every run, 2026-10-03)

- `verify_control_column_scroll.py` — timeout waiting for `.live-param` count.
- `verify_control_surface_component.py` — click on `[data-target-toggle="g0"]`
  times out.
- `verify_control_tab.py` — "a send in one card leaves the others alone",
  "Open in Control adds a card for that Seat".
- `verify_manifest_param_visibility.py` — **"standalone facilitator shows only
  flagged parameters — ['gain', 'gain']"**: Remote renders `gain` twice. Looks
  like a real UI bug. Also "Remote command editor is a visible venue sibling".
- `verify_preset_control_surface.py` — preset journey; will be deleted by
  `65-remove-presets` — don't repair, just confirm.

`verify_manifest_param_visibility` fails the same way at `5506439~1`, so this
predates September.

## Do

For each: real regression → fix the code; drifted test → fix the test and say
what changed. Bisect if the cause isn't obvious. `glean:playwright-gotchas`
applies.
