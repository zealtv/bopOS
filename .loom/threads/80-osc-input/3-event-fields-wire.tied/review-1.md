# Manager review 1 — 3-event-fields-wire

Good work overall: manifest validation, node tag check, simfleet/audition parity and the contract
read well. Three things before landing:

1. **Tag by declared kind on the dashboard fire path (must fix).** `validate_event_command` and
   `osc_bridge.fire_event` now tag from the Python type of the JSON value. JSON loses the
   float/int distinction (`JSON.stringify(1.0)` is `"1"`), so a `float` field fired from the UI
   with a whole value goes out as `i`. The instructions say "`fire_event`: tag each field by its
   kind". When the fired event is declared in the manifest of the target it's sent to (the fleet
   patch in Live/Simulation, the edited patch in Patch Edit — find how the server already picks
   the active manifest for params), coerce each supplied value with `coerce_event_field` so the
   tag follows the declared kind. More values than declared fields is an error. Don't fill
   defaults or clamp here (that's the OSC input stitch). For an undeclared event, keep a sane
   fallback (numbers as `f`, strings as `s`) and say what you chose. Add tests: a float field
   given `1` goes out as `f 1.0`; an int field given `2.0` goes out as `i 2`; a text field
   given a number is rejected. Keep it small; stitch 7 will reuse the same lookup, so a helper
   like "declared event for (manifest, identity)" is welcome.
2. **`git merge main`** again: main now has `6-group-name-rule` (it touched some of the same
   browser fixtures, e.g. `verify_control_tab.py`, `verify_event_control_panel.py`).
3. **Run the full browser tier** (`./tools/run-tests.sh browser`) after the merge and list every
   failing journey in `worker-result.md` with one line on why. The UI still reads `arity`
   (`control-surface.js`, `dashboard-patches.js`); fixing that is stitch 4, so expected failures
   there are fine, but they must be named, and nothing outside event UI may fail.

Then update `worker-result.md` (keep READY FOR REVIEW at the top) and end with `WORKER DONE`.
