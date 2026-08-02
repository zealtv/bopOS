# Verification

Passed browser-free checks:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_cards_grid_css.py
# 7 tests, OK

PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_css_component_ownership.py
# 5 tests, OK

node --check dashboard/static/js/control-host.js
node --check dashboard/static/js/control-column.js
git diff --check

./tools/run-tests.sh fast
# 288 tests, OK
```

The focused Playwright journey now creates four targets and measures both
Control and Remote at 1200px. Each surface must form three columns plus a lone
final-row card, with all four widths equal within one rendered pixel and the
final card sharing the first column's left edge. The existing 1800px Control
check still requires tracks to grow beyond 400px while staying below 560px.

The newly granted filesystem permissions resolved the previous OpenSSL and ICU
launch failures. Chromium then reached macOS process registration but the
custom sandbox denied its Mach service `bootstrap_check_in`, causing launch to
abort before navigation. That capability is not a filesystem/network profile
entry, and no alternate-browser workaround was attempted. No real-browser,
iPad/touch, hardware, audio, OSC, or Pure Data pass is claimed.
