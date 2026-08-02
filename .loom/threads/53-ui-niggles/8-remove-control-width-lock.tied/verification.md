# Verification

Passed browser-free checks:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_cards_grid_css.py
# 7 tests, OK

PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_css_component_ownership.py
# 5 tests, OK

git diff --check

./tools/run-tests.sh fast
# 288 tests, OK
```

`tests/verify_control_column_scroll.py` now resizes Control to 1800px and
requires all four cards to grow beyond 400px while staying equal and below
560px. The preceding implementation would fail at approximately 342px. The
existing 1200px check still requires the sparse final card to share the first
card's left edge.

The focused Playwright journey could not execute in the managed sandbox;
Chromium again aborted because `icudtl.dat` was unavailable. No post-fix
automated browser, iPad/touch, hardware, audio, OSC, or Pure Data pass is
claimed.
