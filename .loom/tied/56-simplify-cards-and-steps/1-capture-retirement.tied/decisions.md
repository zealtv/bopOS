# Decisions — 1-capture-retirement

## The automatic authoring seam is gone

R5 is implemented as deletion. The Control strip and Show edit bar no longer
mount a capture affordance; the dedicated JavaScript and stylesheet are gone;
and no capture verb, model mutation, derived alias, undo offer, or
capture-specific runtime state remains.

The Control strip itself stays because `+ column` is still a tab-scoped action.
Only its right-hand capture slot and the preview panel were removed.

## Preset save and manual Show authoring stay separate

`preset_application.capture_params` and the save drawer's include allowlist
remain the preset-save path. `preset_application.capture_target` also remains:
`Dashboard.capture_preset` still uses it to derive the target stored in a saved
preset. Neither helper belongs to the retired Show-step capture feature.

Preset-reference messages, `apply_preset`, flattening, and ordinary Show model
mutations remain. `verify_show_reference_foundation.py` now exercises the R5
replacement workflow through the real Show inspector: add a message, select
the preset payload mode, and persist a reference to a stored preset.

## One dangling hook found by the browser journey

The first focused browser run exposed a remaining `capture?.handle(event)` at
the start of Show's delegated click handler. With the component variable gone,
every Show click raised `capture is not defined`, blocking unrelated inspector
actions. The hook and its comment were removed; the corrected journey reports
no page errors.

The queued text-kind stitch's component inventory was updated from six
stylesheets to five so it does not attempt to adopt the retired component.
