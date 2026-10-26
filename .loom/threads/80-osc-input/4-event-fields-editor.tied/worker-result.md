READY FOR REVIEW

Commit `3d22df2` (Edit and fire typed event fields in the dashboard). `git merge main` was already up to date. No loom lifecycle changes, no `.pd` edits, no hardware claims (simfleet only).

## What changed
- `dashboard/static/js/dashboard-patches.js`: an event row now holds a nested field list. Field rows reuse the param row's kind controls (`manifestKindControls`, `setManifestParamKind`, one shared binding `bindDeclarationRow`) plus an "optional" checkbox. Add field (max 16), remove, drag-reorder (the reorder code gained a `fields` kind). `arity`/`defaults` are gone. Saves `{name, path?, fields, dashboard}`; blank range/default are dropped and `optional:false` is omitted. Old saves dropped an event's `path`; this one keeps it.
- `dashboard/static/js/event-fields.js` (new, loaded in `index.html` and `facilitator.html`): one control per field kind, name label, default prefill, and wire-limit checks (text 1–255 printable ASCII, no whitespace; number range/integer).
- `dashboard/static/js/control-surface.js`: event row = fire, one labelled control per field, name. A value the wire would refuse is marked `aria-invalid` and the fire is held. Typed values are kept across heartbeat re-renders.
- `dashboard/static/js/show.js`: the event builder, mode default and event picker use declared fields and OSC tags (`f`/`i`/`s`).
- `dashboard/static/css/{style,control-panel}.css`; `patches/README.md` (stale arity text).
- Tests: new `tests/verify_event_fields_editor.py`; `verify_control_surface_component.py` assertion adopted (`data-event-fields` replaces `data-event-arity`).

## Decisions
- Numeric fields use the shared number box (`value-box.js`, which clamps to min/max on commit) rather than a slider, to keep the existing event-row look. Toggle uses `.live-toggle`, enum `.live-enum`, text a text box.
- Field names show as small labels above their control, so a fielded row is taller than a param row. Zero-field events are unchanged.
- Draft persistence is new: previously typed event boxes snapped back to defaults on the next render after blur. Text fields made that unusable.
- Fire sends every field (optional ones at their prefilled default); the server fills nothing.

## Verification
- `./tools/run-tests.sh fast`: Ran 629 tests, OK.
- `./tools/run-tests.sh browser`: every journey PASS, none FAIL (log: `browser.log` here). This includes the three stitch-3 failures (`verify_control_surface_component`, `verify_event_control_panel`, `verify_manifest_param_visibility`).
- New journey checks: authoring five mixed fields, remove and drag-reorder, saved JSON, reload, an invalid (required-after-optional) save refused, fire held for empty or whitespace text, fire carries `[folder, .25, 2, 7, 1]`, simfleet logs `elements=m1s2/spot1/slice000 0.25 2 7 1`, number clamp, Show builder saves `s/f/i/i/i` args.

## Review hardest
- The `bindDeclarationRow` ownership filter (event-level inputs vs nested field inputs share `data-manifest-field`).
- `eventDrafts`/`eventInvalid` keys in `control-surface.js`.
- Simfleet logs don't show OSC tags, so tag fidelity rests on stitch 3's tests.
