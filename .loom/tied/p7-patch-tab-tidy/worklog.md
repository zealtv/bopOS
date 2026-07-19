# p7 patch-tab tidy worklog

## Outcome

- Renamed manifest promotion from `facilitator` to `dashboard` across the
  validator, dashboard server, editor, live surface, demos, and composing docs.
- Legacy `facilitator` loads normalize to `dashboard`; conflicting dual keys
  reject; writes emit only `dashboard`.
- Legacy presentation `group` is ignored on load and stripped on save. The
  Patch editor no longer renders or reasons about it; flat params render in the
  default parameters section.
- The path placeholder now reads `e.g. instrument/marimba`.
- Recorded the ratified compatibility amendment in OSC contract §8 and its
  revision table. No `.pd` files were changed.

## Verification

- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -u .loom/threads/15-show-polish/p7-patch-tab-tidy.stitching/verify_patch_tab_tidy.py`
  — 12/12 passed, including legacy normalization, conflict rejection,
  strip-on-save, Patch-tab DOM terminology/fields/hint, live Dashboard
  promotion, browser errors, and tracked demo manifests.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/tied/pe-3-manifest-editor/verify_pe3_backend.py`
  — 12/12 passed.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -u .loom/tied/pe-3-manifest-editor/verify_pe3_manifest_editor.py`
  — 12/12 passed after amending the tied verifier for the tabbed UI, canonical
  Dashboard field, removed group input, and current engine-route warning.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/tied/2-dashboard-state-editor/verify_param_dashboard_backend.py`
  — 13/13 passed.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -u .loom/tied/2-dashboard-state-editor/verify_param_dashboard_browser.py`
  — 12/12 passed after amending its retired-group expectations.
- `node --check` passed for `dashboard.js`, `facilitator.js`, and `show.js`;
  `py_compile` passed for all touched Python implementation/verifier files.
- Both tracked demo manifests load successfully; `git diff --check` passed.

## Adjacent regression note

The tied live-controls backend verifier passed its 16 promotion/parameter
checks, then reported three pre-existing device-mute expectation failures. Its
browser verifier is stale against the current Seat-card fixture and did not
complete. The p7 focused verifier independently exercised the normalized
promotion through the real `/facilitator` page, so the changed manifest/live
control seam is covered. No hardware, touch-device, audio, or PD verification
was performed.
