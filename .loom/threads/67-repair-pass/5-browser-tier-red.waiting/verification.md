# Browser tier repairs

## Findings and changes

All four repaired failures were test drift, not regressions in the shipped
operator behavior. No product implementation or wire behavior was changed.

- **Column scrolling:** the init-script string contained an uncalled arrow
  function, so it never seeded the four Control targets. Execute the storage
  setup directly. The existing geometry/scroll assertions now exercise the
  intended four-card fixture and pass.
- **ControlSurface component:** Remote derives All/group/Seat cards and has
  no target picker. Remove clicks on nonexistent picker chips and check the
  already-derived group and Seat cards. Scope Seat 2's row/accordion/reload
  assertions by ID because both Seat cards are present.
- **Control tab:** sending to a Seat correctly updates All's aggregate value,
  so byte-identical All markup is the wrong isolation assertion. Await the
  intended Seat value and prove the other Seat value and All target remain
  intact. Open in Control sorts Seat 1 ahead of Seat 5; assert that order
  rather than assuming the newly opened card is appended.
- **Manifest visibility:** `gain` occurs once on All and once on Seat 1,
  correctly following Remote's per-target layout. Assert one flagged row on
  each card, preserving the assertion that unflagged rows are absent. Scope
  the venue-setting label check to the paragraph because the save button also
  contains those words. A first repaired run later exposed a transient missing
  drag rectangle; collect both rectangles from connected nodes together with
  bounded retries before starting the gesture, preserving all reorder checks.

## Explicit preset deferral

The stitch says `verify_preset_control_surface.py` will be deleted by
`65-remove-presets`: **"don't repair, just confirm."** The timeout while waiting
for `installation.seats['1'].preset_dirty === 'missing'` after removing an
applied preset file is confirmed in the complete browser run. It is not
repaired, removed, skipped, or converted to a passing result here.

Consequently the full tier remains red until preset removal. The parent
requires a green browser tier once this stitch is done, so this stitch stays
waiting, anchored to `2-remove-presets`, rather than being tied prematurely.
The four repairs are committed now; after preset removal, resume this stitch
and run the full tier before tying it. Verification docs and current guidance
state the remaining limitation. The CI job continues to surface the failure.

## Commands and results

- Stitch `verify.py`: four repaired journeys passed; per-file
  `verify_*.log` files retain all assertions. The scroll journey and component
  journey also ran during diagnosis; initial logs retain the newly exposed
  scoping/drag failures and the successful scroll result.
- `./tools/run-tests.sh fast`: all 377 tests passed (`fast.log`).
- `./tools/run-tests.sh browser`: all 25 journeys attempted; 24 passed, with
  only `verify_preset_control_surface.py` failing at the documented missing
  applied-file timeout (status 1). Complete results are in `browser.log`.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m
  py_compile` for all four touched test files and stitch `verify.py`: passed.
- `git diff --check`: passed.

Real dashboard and simfleet journeys ran with temporary fixtures on macOS.
Chromium and loopback test processes required unsandboxed execution. No Pi,
audio, Pd, iPad, or installation-LAN checks were performed. Existing user
changes to `dashboard/shows/test.json`, `.codex/`, and `.obsidian/` are outside
this commit.
