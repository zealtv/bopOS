# Verification

Red/green focused regression on 2026-08-02:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  tests/verify_show_generator_drawer.py
```

Before the implementation, editing an LFO phase failed because both
`#show-param-value` and `#show-param-slider` disappeared. Afterward the journey
passes 17 checks covering the persistent row, the shared 58px / slider / 18px
geometry, cyan closed-generator state, slider takeover, number-box takeover,
Stop wire form, drawer behavior, and absence of browser errors.

Pre-tie checks:

```sh
node --check dashboard/static/js/show.js
git diff --check

./tools/run-tests.sh fast
# 266 tests, OK

./tools/run-tests.sh browser
# 22 journeys passed directly. verify_interaction_guard had a one-off existing
# focus-release timing failure; verify_show_generator_drawer exposed a
# non-atomic two-read geometry assertion while a heartbeat replaced the row.

PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  tests/verify_show_generator_drawer.py
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  tests/verify_interaction_guard.py
# both affected journeys passed after making the geometry read atomic.
```

No hardware, Pure Data, audible, real-LAN, or touch-device checks apply.
