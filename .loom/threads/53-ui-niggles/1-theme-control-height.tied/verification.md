# Verification

Red/green focused check on 2026-08-02:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  tests/verify_ground_and_card.py
```

Before the CSS change it failed only at the wide 1280px layout in both themes:
`header=40px, theme=40px, execution=38px`. After the change it passed at
1280px, 900px, and 700px in both themes, along with every existing §12 surface
check.

Pre-tie suites:

```sh
./tools/run-tests.sh fast
# 266 tests, OK

./tools/run-tests.sh browser
# 22 journeys passed; the two preset journeys reached stale `=== true`
# assertions introduced by the preceding dirty-reason stitch.

PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  tests/verify_preset_control_surface.py
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  tests/verify_preset_editor.py
# both repaired journeys passed; no browser behavior remains failing.
```

No hardware, Pure Data, audible, or touch-device behavior is involved.
