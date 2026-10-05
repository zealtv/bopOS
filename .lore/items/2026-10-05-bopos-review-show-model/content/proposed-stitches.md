# Proposed stitches from 74/4 (show model review)

Grouped by file and mechanism: three repairs and two cleanups. F-numbers refer to `findings.md`.

## `show-number-boundary` — show_model.py

- **Parent:** `67-repair-pass`
- **Findings:** F1, F2, F3, F8 (F6 if it needs no ruling).
- **Goal:** Make every show input fail closed at one boundary: files, WS edits, and `set_live_automation`'s use of `clean_arg`. Malformed numbers return a validation error or a read-only load, never an exception. `i` args are integral int32, `f` args finite float32. Addresses follow the OSC character rules.
- **Done when:** the F1/F2/F3/F8 cases in `reproduce.py` now meet the fix (a damaged show loads read-only, an edit returns an error, a non-int32 `i` is rejected); a non-open show with `1e999` no longer breaks `state.public()`; existing valid shows load unchanged; `test_show_model`/`test_shows` and the fast suite pass. Whether stored string and fractional ints are rejected or tolerated is decided first, and goes to Bob if it is not clear-cut.

## `show-playback-consistency` — show_engine.py + server.py Show handlers

- **Parent:** `67-repair-pass`
- **Findings:** F4, F5, F9, and F6 (a minimum period for infinite repeats).
- **Goal:** Make `playback` describe only steps that exist and are actually timing. A failing message send is logged and skipped. Undo stops steps that are missing from the restored document. A missing step on expiry drops its entry. `remove_item` stops the step only once the removal is saved. Infinite repeats cannot re-arm faster than a stated floor.
- **Done when:** the F4/F5/F6 cases in `reproduce.py` meet the fix; after each case `show_playing()` is false or truthful, and Clear Show and show management are not refused; a refused `remove_item` leaves playback untouched; a floor that becomes visible in the UI has Bob's ratification.

## `show-step-counts-cache` — state.py

- **Parent:** `69-complexity`
- **Findings:** F7.
- **Goal:** Stop `state.public()` from reading and validating every show file on each snapshot. Cache step counts by file identity, or update them when shows change.
- **Done when:** the F7 counter shows no repeated loads for unchanged files; counts stay right after edit, create (including copy), rename, delete, and an outside change to a file; invalid shows still report `None`.

## `show-patch-ops-use-cleaners` — show_model.py

- **Parent:** `69-complexity`, after `show-number-boundary`.
- **Findings:** F12.
- **Goal:** Have `update_step` and `update_message` merge the patch and validate it through `clean_step`/`clean_message`, so each rule exists once.
- **Done when:** the file is about 40 lines shorter; the UI-visible error texts the tests check are unchanged (or the UI is confirmed not to depend on them); the show tests and the Show journeys (`verify_show_targets`, `verify_clear_show`) pass.

## `show-post-66-leftovers` — show_model.py, show_engine.py

- **Parent:** `69-complexity` (70 is tied; reopen it instead if the lead prefers).
- **Findings:** F10, F11.
- **Goal:** Make comments describe today's shows (several per project, `shows/<name>.json`, playback engine present). Remove the engine's unreachable branches. Settle the show document's `name` field: stop writing it, or document it as advisory, while `tools/migrate_shows.py` keeps reading it.
- **Done when:** no comment mentions a "future" engine, `TODO(stitch 3)` or `show.json` as the live location; the engine branches are gone and the show tests pass; the decision on `name` is written in the stitch. Removing the legacy `show.json`, the `.pre-*` backups and `migrate_shows.py` is left to Bob and is not part of this stitch.
