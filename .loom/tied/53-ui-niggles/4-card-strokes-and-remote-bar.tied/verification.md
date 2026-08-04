# Verification

Passed focused browser-free checks:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_card_identity.py
# 5 tests, OK

PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_cards_grid_css.py
# 4 tests, OK

PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_remote_live_bar.py
# 3 tests, OK

node --check dashboard/static/js/group-slots.js
node --check dashboard/static/js/control-host.js
node --check dashboard/static/js/facilitator.js
node --check dashboard/static/js/dashboard.js
git diff --check
```

Pre-tie suite:

```sh
./tools/run-tests.sh fast
# 285 tests, OK
```

The focused real-browser journey was extended to measure the stable Control
and Remote strokes, 480px ceiling, and Remote bottom bar. It could not execute
in this managed sandbox. Playwright first hit the denied system OpenSSL config;
with `OPENSSL_CONF=/dev/null`, Chromium launched but aborted because its bundled
`icudtl.dat` was unavailable to the sandbox. No browser, iPad/touch, hardware,
audio, OSC, or Pure Data verification is claimed.
