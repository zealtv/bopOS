# 2-reference-schema-meaning

**Status:** ready · independent of `1` · hard prerequisite for `4`
**Goal:** `reference.schema` means "the schema this message was authored
against" — at both the stamp and the comparison.

## The bug

- **Stamp:** `presetReference()` in `show.js` stamps `entry.schema` from
  `preset_catalog` = the schema **the preset file was saved against**.
- **Compare:** `show_reference_warnings` compares it with **the patch's current
  schema**.

Result today: choose a preset that's already drifted (shown `*` in the
dropdown) and the brand-new message warns `schema_drift` immediately, with no
fix available. For `4`: Accept would stamp a value the picker never produces,
so the next picker touch silently undoes it.

## Change

- `preset_catalog()` (`server.py`) also carries the patch's **current** schema
  fingerprint; `presetReference()` stamps that.
- Keep `entry.schema` and the `drift` flag as they are — that's a different fact
  (preset file vs current manifest) and drives the inspector's correct "preset
  schema differs from the current patch" line.
- Your call where the current fingerprint lives; prefer leaving
  `preset_store.list`'s per-entry shape untouched (Control reads it too).
- Record in `decisions.md` why there are two schema fingerprints, so nobody
  "dedupes" them.

## Done when

- A test with a real `Dashboard` + real preset: author a reference against a
  preset whose saved schema differs from current → `show_warnings()` returns no
  `schema_drift`. Fails before the change.
- One explicit assertion each that the Control `drift` flag and the inspector
  line are unaffected.
- `tools/run-tests.sh fast` + `tests/verify_preset_control_surface.py` green.
