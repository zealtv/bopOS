# Progress — 7-preset-slot

2026-07-27. Fifth slice of the ratified control-panel design shipped: the
provisional preset row now renders in both hosts of the shared surface.

## What landed

- `control-surface.js` — `presetRow(patch, key)`, exported on the component.
  Patch name (live) + preset `<select>` + `new`/`save`/`del`, everything but
  the name inert.
- `facilitator.js` — the Control tab / standalone facilitator renders the row
  between the card head and `.promoted-controls`, on every card that has
  parameters. `liveCard` takes the schema's patch name.
- `dashboard.js` — the Device tab renders the same row at the top of the
  control body.
- `control-panel.css` §16 — row chrome; momentary radius on new/save/del per
  design-language §8; the visually-hidden note.

## Decisions taken here

1. **The row is per panel, not per privileged card.** The mockup draws it on
   All Seats, but a preset is per target — the shipping venue-preset shelf
   already scopes by target (`presetScope()`), and `41`'s capture-as-step
   stores "the current target→preset arrangement". So every card that has
   parameters gets the slot.

2. **`aria-describedby`, not `title` alone.** The stitch asked for an
   explanatory title/aria-description. A disabled control is not focusable, so
   its `title` is never announced; each inert control points at a
   visually-hidden note naming `41-preset-primitive`, and keeps the `title`
   for the pointer.

3. **The Device tab's patch line lost the patch name.** The head line used to
   read `alpha · fleet patch`; the preset row now names the patch, so the head
   keeps only the provenance (`fleet patch` / `pinned to this device`). No
   test pinned the old string, and `verify_device_control_panel.py`'s "the
   panel names the patch it is showing" check still passes — the name is now
   in the row.

4. **One rule, not two.** `facilitator.css` gives `.promoted-controls` its own
   top rule; with the preset row above it that doubled. The row's rule wins
   (it is the one the mockup draws, where the mockup draws it) and the
   following block's is suppressed.

## Verification

- `tests/verify_control_tab.py` — six new checks: the slot exists, names the
  live patch, offers `new`/`save`/`del`, sits between the header and the
  rows, is entirely inert, and every inert control resolves an explanation
  naming `41-preset-primitive`. PASS.
- `tests/verify_device_control_panel.py` — the same slot on the Device host,
  above the rows, inert, naming the patch. PASS.
- Full `tools/run-tests.sh browser`: all 12 verifiers PASS.
- Screenshots (dark + light, Control tab at 1440px) reviewed with Bob live —
  approved 2026-07-27 ("preset slot looks great").

Not built, by design: any preset behavior. `41-preset-primitive` remains
gated behind `44-event-plane`.
