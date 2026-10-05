# 69/8 Show model tidy — verification

Implemented in `.worktrees/69-8-show-tidy`, branch `stitch/69-8-show-tidy`.

Patch operations merge only their allowed fields and clean through the document
validators. Validators optionally collect edit errors, preserving the existing
wording and priority without duplicating validation rules. Numeric boundaries,
`ShowEngine.set_show`, send-failure containment and `MIN_REARM_S` remain intact.

Removed unreachable engine handling for unsupported message kinds, non-list
resolver results and empty then-action lists. Updated model comments to current
project storage and playback. Saving omits the advisory `name`; in-memory names
and legacy-name reading (including migration) remain supported.

Final checks, run as plain commands from the worktree root:

- `./tools/run-tests.sh fast`: 612 tests, OK.
- `~/.venvs/bopos/bin/python -m unittest tests.test_show_model tests.test_shows`:
  51 tests, OK.
- `~/.venvs/bopos/bin/python tests/verify_show_targets.py`: 9 checks, 0 failures.
- `~/.venvs/bopos/bin/python tests/verify_clear_show.py`: PASS.
- `~/.venvs/bopos/bin/python tests/verify_project_shows.py`: PASS.
- `~/.venvs/bopos/bin/python -m py_compile dashboard/show_model.py dashboard/show_engine.py tests/test_show_model.py tests/test_shows.py tests/test_project_menu.py`: PASS.
- `git diff --check`: PASS.

New regression coverage checks exact edit errors and priority, copy-on-write
failure, protected identity/message fields, normalization, omission of stored
names and continued loading of legacy names. Updated persisted-document
expectations and cleaned the playback-order fixture at the model boundary.
Removed the redundant direct-engine unsupported-kind test; the model rejection
test remains. Fixed the show-model test's fixture import so the requested
root-level unittest command runs.

Initial runs found old storage/engine fixture expectations; corrected before
the final passing runs. Browser checks required unsandboxed loopback access.
Show Targets twice collided with the other worktree's UDP 5551; waited and
retried successfully without killing any processes.

No hardware, Pd, audible audio, real LAN or touch checks were run. Legacy
`show.json`, `.pre-*` backups and `tools/migrate_shows.py` were left intact.
No commits or loom lifecycle commands were performed; Claude owns review and
landing.
