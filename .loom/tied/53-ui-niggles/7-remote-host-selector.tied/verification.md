# Verification

The running server was inspected directly:

```sh
curl -sS http://localhost:8080/css/facilitator.css | \
  rg 'control-column-host(\.control|\{)'
```

It returned the corrected current rules: the same-element derived host is
uncapped and its direct cards region is `display:flex`. This rules out stale
server assets, although Bob may still need to reload the already-open page.

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

The bundled Chromium journey remains blocked by unavailable `icudtl.dat` in
the managed sandbox. An additional attempt to launch the installed system
Firefox through Playwright reached Firefox but aborted because stock Firefox
does not provide Playwright's `-juggler-pipe` interface. No post-fix automated
browser, iPad/touch, hardware, audio, OSC, or Pure Data pass is claimed.
