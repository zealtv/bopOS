# Verification

## Results

- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_manifest.py`
  — 11 tests passed.
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_show_model.py`
  — 9 tests passed; the stored `i`/`f`/`s` argument grammar is unchanged.
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_engine_ready_replay.py`
  — 7 tests passed.
- `./tools/run-tests.sh fast`
  — 185 tests passed.
- `./tools/run-tests.sh browser`
  — all 12 living browser journeys passed on the final run.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python
  tests/verify_manifest_param_visibility.py`
  — focused rerun passed, including the five-option `kind` select, absence of
  the old `type` selector, and enum/toggle field reshaping.
- `node --check` passed for `dashboard.js`, `control-surface.js`, `show.js`,
  and `param-generator.js`.
- `python -m py_compile` passed for every touched Python runtime module.
- `python/manifest.py <patch-directory>` accepted every
  `patches/*/bopos.patch.json`.
- `git diff --check` passed.

## Browser rerun note

The first browser run exposed a migration defect: `simfleet.py` and
`audition.py` import the manifest module as `patch_manifest`, but the new wire
type helper was initially called through `manifest`. Simulator parameter replay
therefore crashed and several journeys timed out at discovery. The alias was
fixed; the focused control-surface journey and then the complete browser suite
passed.

## Boundary

This is a declaration-only break. Existing param values and automation still
emit the same OSC `f`, `i`, and `s` tags. Events, `/e/*`, `/cue` retirement,
Pure Data edits, hardware, and audible behavior were not changed or tested in
this stitch.
