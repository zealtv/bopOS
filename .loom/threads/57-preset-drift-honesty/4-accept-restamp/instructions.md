# 4-accept-restamp

**Status:** blocked on `2-reference-schema-meaning` and `3-drift-marks`
**Goal:** an **Accept** button that records the show as authored against the
current patch — persisted, one undo step (Bob, 2026-08-03).

## Mutation — `show_model.py`

`restamp_references(show, patch, reference) -> (new_show, [message_uid…], error)`,
beside `flatten_preset_message`.

- Re-stamps **every** preset message for that patch in one mutation; other
  patches untouched. Idempotent on already-current messages.
- Re-runs `clean_message`, so a bad stamp is refused.
- Returns an error when the show has no reference to `patch` — otherwise
  `apply_show_mutation` no-ops silently and it looks like success.

## Server — `server.py`

New verb `restamp_references`, payload `{"patch": "<name>"}`, next to
`flatten_preset_message`. Build the reference from
`_current_patch_fingerprint(patch)` + `schema_fingerprint(live_control_manifest(patch))`;
`ws_error` on `PresetStoreError`. Then `apply_show_mutation(...)`.

Must be server-side: `preset_patches()` only covers the fleet patch, editor
patch and device pins, so the client can't build references for other patches.

## Button

`Accept`, in `3`'s inspector block beside `#show-flatten-preset`. Title:
*"Record this show as authored against the current `<patch>`"*. Word ratified
by Bob — changing it needs a fresh ruling.

## The safeguard, as a test

Because applicability never reads the reference, Accept clears the provenance
mark but **cannot** clear `preset_dropped` / `preset_clamped`. Pin it:

> **acknowledgement-does-not-hide** — re-stamp a show whose preset has a dropped
> entry; `preset_dropped` remains, `patch_drift` is gone.

Docstring should say this test exists to stop anyone gating resolution on the
hash.

## Done when

- `tests/test_show_model.py`: rewrites every message for the patch, leaves
  another patch's messages byte-identical, refuses an invalid reference, errors
  when unreferenced; plus the safeguard test above.
- `tests/verify_show_reference_foundation.py`: Accept rewrites `reference` in the
  saved show JSON on disk and removes the mark; undo restores both in one step.
  Gotchas 16 + 22 (wait on the exact element you click), 8, 17.
- `tools/run-tests.sh fast` + `browser` green.
