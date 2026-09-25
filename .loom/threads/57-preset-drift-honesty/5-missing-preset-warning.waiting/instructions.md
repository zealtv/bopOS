# 5-missing-preset-warning

**Status:** waiting on Bob
**Question:** should a Show step pointing at a deleted or corrupt preset warn in
the Show tab, or is the silent skip at playback acceptable?

## Today

No warning at all. At playback the failure goes to `log.warning` in
`server.py` and the step does nothing. `preset_store.list` already keeps invalid
entries with an `error`, so the information exists.

## For / against

- **For:** it's a real broken-show condition, the only unrecoverable one, and
  playback is too late to find out.
- **Against:** it adds a panel line during a pass meant to remove them, and a
  missing slug is arguably visible in the inspector dropdown.

Parked rather than bundled because of Bob's rule: *"fix and simplify things
before making them more complicated."*

## If ruled in

Small, after `1`: `presets[slug]` absent or `error` set → `missing_preset`,
severity warn, collected per (patch, slug). One branch in
`show_reference_warnings`, one test in `tests/test_show_model.py`, one fixture in
`tests/test_preset_application.py` that deletes a preset under a reference.
