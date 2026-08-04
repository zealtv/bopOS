# Verification

Passed focused browser-free checks:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_cards_grid_css.py
# 5 tests, OK

PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_css_component_ownership.py
# 5 tests, OK

git diff --check
```

The first fast run caught the Remote host styling `.live-card`'s `max-width`,
which violated component ownership. Moving both bounds onto `.target-card` in
the shared component stylesheet resolved it. The clean pre-tie run passed:

```sh
./tools/run-tests.sh fast
# 286 tests, OK
```

`tests/verify_control_column_scroll.py` now measures a 1200px Control layout
that produces three cards followed by one sparse-row card, asserting that the
last card shares the first card's left edge and remains within 340–560px. It
also checks both hosts use flex layout and respect the bounds.

The focused browser journey could not execute in this managed sandbox. With
`OPENSSL_CONF=/dev/null`, Chromium launched but aborted because its bundled
`icudtl.dat` was unavailable to the sandbox. No real-browser, iPad/touch,
hardware, audio, OSC, or Pure Data verification is claimed.
