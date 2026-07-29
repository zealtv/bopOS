# Verification — 1-reference-foundation

## Focused

- `node --check dashboard/static/js/show.js` — PASS.
- `~/.venvs/bopos/bin/python -m py_compile dashboard/server.py
  dashboard/show_engine.py dashboard/show_model.py dashboard/state.py
  tests/test_show_model.py tests/verify_show_reference_foundation.py` — PASS.
- `~/.venvs/bopos/bin/python tests/test_show_model.py` — PASS, 18 tests.
- `~/.venvs/bopos/bin/python tests/verify_show_reference_foundation.py` —
  PASS, 7 checks. Covers load/authoring warning, picker name storage and
  rendering, reference copy/paste, one-entry undo, and browser errors.
- `node --check`, compile, and `git diff --check` — PASS after final edits.

## Repository tiers

- `./tools/run-tests.sh fast` — PASS, 236 tests.
- `./tools/run-tests.sh browser` — 14 verifier files passed; 3 files were red
  in that run:
  - `verify_control_surface_component.py`: enum handler race;
  - `verify_generator_drawer.py`: both generator-stop tick assertions;
  - the new reference verifier missed initial Show full-state under suite load.

The new verifier was hardened to reconnect on that documented initial-listener
race and then passed standalone, 7/7. The other two failures reproduce from an
isolated `git archive HEAD`, before this stitch: the enum send remains red
(and the baseline run also hit its existing accordion timing cascade), and
both generator-stop tick assertions remain red with the same continuing-tick
signature. No control-surface, generator, simulator, or automation code is
changed by this stitch.

Therefore the changed Show/reference surface and the complete browser-free
suite are green; the repository-wide browser command is honestly not green
because of confirmed pre-existing failures outside this stitch.

## Boundaries

No Pure Data, hardware, audible, real-LAN, or iPad checks were required or
performed. Named target resolution was exercised through the model,
Show-engine callback, real dashboard persistence, and Chromium UI; no real
node was needed because the wire selector boundary is host-side.
