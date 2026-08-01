# Verification

## Focused browser journey

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_manifest_param_visibility.py
```

Result: PASS. The journey covers:

- parameter drag within Parameters;
- event drag within Events;
- cross-section drag rejection;
- unchanged nested parameter identities;
- persisted `params` and `events` JSON order;
- post-save Control-panel parameter and event order;
- no browser page errors.

The journey uses `page.evaluate()` for explicit scrolling before pointer
gestures, per the repository Playwright guidance.

## Full pre-tie suite

Command:

```sh
./tools/run-tests.sh all
```

Result:

- fast: 196 tests passed;
- browser: 14/14 living Playwright journeys passed.

## Static checks

```sh
node --check dashboard/static/js/dashboard.js
~/.venvs/bopos/bin/python -m py_compile \
  tests/verify_manifest_param_visibility.py
git diff --check
```

All passed.

## Untested boundary

No physical hardware, iPad/touch device, or audible behavior was tested. The
pointer interaction is exercised in Chromium with a real mouse gesture; the
implementation uses Pointer Events and `touch-action: none` for touch input.
