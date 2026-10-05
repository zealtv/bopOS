# Show model review addendum — 2026-10-05

Reviewed main at `67ede5f7bc61c38a0eb52389bedfe5edab2b9aef`. Read in full: `dashboard/show_model.py` (713 lines, down from the 921 the stitch named), `dashboard/show_engine.py`, the Show handlers in `dashboard/server.py` (`apply_show_mutation`, `undo_show`, `manage_show`, `load_project_show`, the WS dispatch), the show-file functions in `dashboard/state.py`, and `tools/migrate_shows.py`. Eight findings are confirmed by bounded software reproductions; four are labelled *likely*. The highest priority is F1: one show file holding an out-of-range number stops the dashboard from starting, and stops every state snapshot while that show is in the project. Next are the numeric-boundary gaps (F2, F3) and two ways playback is left showing a step as playing with no timer (F4, F5). Runtime code was not changed. No hardware, audio engine or browser verification is claimed.

Presets are fully out: `show_model.py` and `show_engine.py` contain no preset or capture code, and every `show_model` function has a runtime caller. `66-projects` has already done the move this stitch anticipated. A project now has several shows in `projects/<project>/shows/<name>.json`, with the file name as the show's name. The model never learned the paths, so it needed no change. What 66 left behind is stale prose, a vestigial `name` field, and legacy files kept on purpose (F10). Undo is otherwise sound: it holds the edit lock, deep-copies, is capped at 100, is cleared on show or project change, and stays blocked while a show file is write-blocked.

## Reproduction and test evidence

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python .loom/threads/74-review-remaining/4-review-show-model.stitching/reproduce.py
(cd tests && ~/.venvs/bopos/bin/python -m unittest test_show_model test_shows)
```

`reproduce.py` labels F1–F8 and asserts each observed defect. It opens no sockets and starts no engines. Engine cases use a fake bridge that records sends, and F4 alone runs the real `OSCBridge._datagram` builder without a socket. Fixtures go only into one `/tmp/bopos-74-4-*` directory, and the longest case lasts 0.25 s. Output is kept in `reproduction.log`. The existing show tests ran **37 tests, OK** (`show-tests.log`). The full fast suite was not run, because nothing was changed.

## F1 — One out-of-range number in a show file stops the dashboard

- **File:line:** `dashboard/show_model.py:93`, `:245`, `:711` (`except ValueError` only); callers `dashboard/server.py:218` (startup `load_project_show`), `dashboard/state.py:458` → `:1376` (`public()` → `show_step_counts`).
- **Severity:** High.
- **Status:** **CONFIRMED** — F1 in `reproduce.py`.
- Python's `json` reads `1e999` as `inf` and keeps a 400-digit literal as an exact int. Three values in a show file each raise `OverflowError` from `load_show`: `{"type":"i","value":1e999}` (`int(inf)`), an `f` arg holding a 400-digit integer (`float()`), and a 400-digit `duration_s`. `load_show` promises `(empty, False)` for a damaged file, but it only catches `ValueError`. If the file is the open show, `Dashboard.__init__` raises and the dashboard never starts. If it is any other show in the project, `show_step_counts` raises on every `state.public()`. That means every state broadcast and every new WebSocket connection, because the connect handshake sends `public_state` first. The read-only rule for damaged files (`f78fe71`) is therefore bypassed.
- **Suggested route:** 67 repair. Make show-file loading fail closed for every malformed number: guard the conversions in `clean_arg` and `clean_step`, and catch the whole class at `load_show`. Verify that the open show and a non-open show with these values both load read-only, and that state snapshots continue.

## F2 — Edit payloads with huge numbers raise instead of returning an edit error

- **File:line:** `dashboard/show_model.py:461`–`462` (`math.isfinite` on an int), `:93` via `add_message`/`update_message`; dispatch `dashboard/server.py:1297`–`1329`, connection loop `:353`–`356`.
- **Severity:** Medium.
- **Status:** **CONFIRMED** — F2 in `reproduce.py`.
- `update_step` with `duration_s: 10**400` and `add_message` with an `i` arg of `Infinity` (a JSON `1e999`) both raise `OverflowError`. Every other bad edit gets a polite `ws_error`. These escape `handle_ws`, end the client's receive loop, and drop its WebSocket. Nothing is saved and no state is corrupted. The browser UI does not produce these values; a raw client does.
- **Suggested route:** 67 repair, in the same stitch as F1, because it is the same conversion boundary. Each malformed number should return the normal error and leave the show unchanged.

## F3 — Show args are coerced, and `i` is not held to int32

- **File:line:** `dashboard/show_model.py:90`–`98`; wire `dashboard/osc_bridge.py:461`–`467`, `:450`–`453`.
- **Severity:** Medium.
- **Status:** **CONFIRMED** — F3 in `reproduce.py`.
- `clean_arg` converts values rather than checking them. An `i` of `1.9` is stored as `1`, an `i` of `"12"` as `12`, and an `f` of `"1e5"` as `100000.0`. An `i` value is never range-checked. `2**31` is stored, and python-osc then sends it with type tag `h` (int64), a tag the contract and Pd do not use. `2**64` is stored and raises `BuildError` at send time, and `_send_to` catches only `OSError` (see F4). This is the show-side counterpart of core-libs F3. The same `clean_arg` also guards `set_live_automation` (`server.py:550`).
- **Suggested route:** 67 repair, in the same stitch as F1/F2. Reject non-integral or out-of-range `i` and non-numeric strings instead of coercing them. Decide whether existing stored strings and fractional ints should load or be rejected. That choice touches stored shows, so if it is not obvious, put it to Bob (decision-gates).

## F4 — A send failure leaves a step "playing" with no timer

- **File:line:** `dashboard/show_engine.py:141`–`143`, `:205`–`209`, `:236`–`239`; `dashboard/osc_bridge.py:450`.
- **Severity:** Medium.
- **Status:** **CONFIRMED** — F4 in `reproduce.py`, using the F3 `2**64` arg.
- `_begin` records the step as playing before `_emit_messages`. When a send raises a non-`OSError` exception, `step_start` raises out to the WS handler and the step is left playing with no timer. From the timer path, `_on_expiry` raises inside a fire-and-forget task (`ensure_future`, so the exception is never retrieved) with the same result. `show_playing()` then stays true, which refuses Clear Show and new/open/rename/delete show until someone presses Stop all. One bad message also stops the later messages of that step from sending.
- **Suggested route:** 67 repair. Contain per-message send failures in the engine: log and skip that message, keep the step's timer consistent, and never strand a playback entry. Do this together with F5, because both repair playback-state consistency.

## F5 — Undo that removes a playing step leaves a ghost playback entry

- **File:line:** `dashboard/server.py:1496`–`1508` (`undo_show`); `dashboard/show_engine.py:199`–`203`.
- **Severity:** Medium.
- **Status:** **CONFIRMED** — F5 in `reproduce.py`.
- `remove_item` stops a step before deleting it (`server.py:1312`), but `undo_show` swaps in the previous document without checking playback. The repro adds a step, starts it, and undoes the add. When the timer fires, `_on_expiry` finds no step and returns early. The entry stays `playing` forever, with `remaining_s` 0, and `show_playing()` stays true, with the same refusals as F4. The same happens when undo removes a duplicated step. Undo of a duration or then-action edit on a playing step is harmless: the next iteration uses the new values.
- **Suggested route:** 67 repair, with F4. Undo should stop any playing step that is missing from the restored document, and `_on_expiry` should drop the entry of a step that no longer exists.

## F6 — A tiny positive duration defeats the zero-duration busy-loop guard

- **File:line:** `dashboard/show_model.py:246`–`255`, `:461`–`464`; `dashboard/show_engine.py:241`–`242`.
- **Severity:** Medium.
- **Status:** **CONFIRMED** — F6 in `reproduce.py` (fake bridge, 0.25 s).
- The model rejects `duration_s == 0` with infinite `play_count`, because "an infinite loop needs positive duration or it busy-loops". `1e-9` with `play_count: null` is accepted. The engine then re-arms every loop turn: about 30,000 sends per second on the review machine, every one a real UDP datagram to the fleet. The cause is a mistake in the Show tab, not an attack. The guard exists for exactly this case.
- **Suggested route:** 67 repair, small. Enforce a minimum period for infinite repeats in the model, or a minimum re-arm delay in the engine. A visible minimum duration is a user-facing rule, so if the floor is not already implied by the design note, propose it to Bob.

## F7 — Every state snapshot loads and validates every show file

- **File:line:** `dashboard/state.py:458`, `:1371`–`1378`.
- **Severity:** Low (efficiency).
- **Status:** **CONFIRMED** — F7 in `reproduce.py` (3 snapshots × 5 shows → 15 loads).
- `public()` builds `show_steps` for the project menu by reading and fully cleaning every show file. It does this synchronously, on the event loop, for every `state` broadcast and every connection. State broadcasts are frequent (device chatter, live params), so the cost grows with shows × broadcasts. This is also the path that turns F1 into a failure of every snapshot.
- **Suggested route:** 69 structure. Cache counts by file mtime/size, or update them when shows change (edit, create, rename, delete). Check that a show edited in another process still shows a sensible count.

## F8 — Show addresses accept text that is not an OSC address

- **File:line:** `dashboard/show_model.py:111`, `:609`.
- **Severity:** Low.
- **Status:** **CONFIRMED** — F8 in `reproduce.py`.
- The only rule is "starts with `/`, no outer whitespace". `/`, `/a b#` and `/x//y` all validate. OSC 1.0 forbids space and `#` in address parts, and an empty part is meaningless. python-osc builds these addresses, so receivers get datagrams they cannot route.
- **Suggested route:** 67 repair, folded into the F1–F3 boundary stitch. Validate address parts against the OSC character rules, and keep raw addresses such as `/pt` working.

## F9 — `remove_item` stops the step even when the removal is refused

- **File:line:** `dashboard/server.py:1312`–`1313`.
- **Severity:** Low.
- **Status:** *likely* — static reading; not reproduced, because it needs a live `Dashboard`.
- `step_stop` runs before, and outside, the edit lock. If the mutation then fails (write-blocked show, failed save, unknown uid), the step has already stopped and the user gets "The show could not be saved." with playback changed anyway.
- **Suggested route:** 67 repair, together with F4/F5. Stop the step inside `apply_show_mutation`, after the save succeeds, so it follows the same rule as undo.

## F10 — Leftovers from the move to several shows per project

- **File:line:** `dashboard/show_model.py:14`–`16` and `:533`–`535` ("future playback engine (stitch 3)", `TODO(stitch 3)`, both now done); `:682`–`685` ("the project's one show, projects/<project>/show.json"); `name` field `dashboard/server.py:1362`, `dashboard/state.py:1420`, `dashboard/server.py:1401`–`1402`.
- **Severity:** Low (maintainability).
- **Status:** *likely* — static review.
- The comments describe the model before 66. A show's name is now its file name: `load_project_show` overwrites `doc["name"]`, and `rename_show` renames the file and changes the in-memory docs but not the `name` stored inside the file. The stored field is therefore stale after a rename, and only `tools/migrate_shows.py` still reads it, to pick a file name for a legacy `show.json`. Locally, `dashboard/projects/bopOS/` still holds `show.json`, `project.json.pre-shows` and `project.json.pre-sites`. These are gitignored, kept on purpose by the migration, and no longer read by any code.
- **Suggested route:** 70 dead code (now tied, so this goes to a new 69 child or a reopened 70). Fix the stale comments. Stop writing `name` into show files, or document it as advisory, but keep reading it for migration. Bob decides when the local legacy files and `migrate_shows.py` can go; do not delete them in a sweep.

## F11 — Unreachable defensive branches in the engine

- **File:line:** `dashboard/show_engine.py:148`–`150` (message `kind` ≠ `osc`), `:152`–`155` (tuple or non-list selectors), `:280`–`281` (empty `then_actions`), `:395` (`step.get("then_actions", [])`).
- **Severity:** Low.
- **Status:** *likely* — static. The model guarantees `kind == "osc"` and non-empty `then_actions`, and the server's `resolve_targets` lambda always returns a list.
- **Suggested route:** 70 dead code, with F10.

## F12 — Patch operations repeat the item validators

- **File:line:** `dashboard/show_model.py:440`–`485` versus `:224`–`269`; `:594`–`633` versus `:101`–`130`.
- **Severity:** Low (maintainability).
- **Status:** *likely* — static. The duplication is why F2's `update_step` gap exists separately from `clean_step`.
- `update_message` already ends with `clean_message(candidate)`, so its per-field checks only choose an error message. `update_step` re-implements the duration, play-count and then-action rules by hand. Having each patch op merge the patch and then call the single `clean_*` validator removes about 40 lines and one source of drift.
- **Suggested route:** 69 structure, after the F1–F3 repair, so that repair lands once in `clean_*`. Keep the specific error texts the UI shows, or confirm that it doesn't depend on them.
