# Verification

Bob's 1920px Firefox screenshot supplied the failing visual evidence: Remote
rendered every target in one approximately 560px column despite ample width.

Passed browser-free checks:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_cards_grid_css.py
# 6 tests, OK

PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_css_component_ownership.py
# 5 tests, OK

git diff --check

./tools/run-tests.sh fast
# 287 tests, OK
```

The focused browser journey now requires both Remote's page host and its real
`.control-column-cards` region to compute to `display:flex`, then measures four
derived cards for equal responsive widths within the 560px ceiling.

The journey could not execute in this managed sandbox. With
`OPENSSL_CONF=/dev/null`, Chromium launched but aborted because its bundled
`icudtl.dat` was unavailable to the sandbox. No post-fix real-browser,
iPad/touch, hardware, audio, OSC, or Pure Data verification is claimed.
