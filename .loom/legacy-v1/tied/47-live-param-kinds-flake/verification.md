# Verification

## Focused and static checks

- `~/.venvs/bopos/bin/python tests/verify_live_param_kinds.py`
  — passed after the final change, including the new focus/handler assertion
  and all toggle, float, integer, enum, persistence, wire, and page-error
  checks.
- `node --check dashboard/static/js/control-surface.js` — passed.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m
  py_compile tests/verify_live_param_kinds.py` — passed.
- `git diff --check` — passed.

## Required repeated browser verification

After the final pointer/keyboard guard separation:

- `./tools/run-tests.sh browser` — **5 consecutive full runs passed**.
- Each run passed **14/14 living browser journeys**, including
  `verify_live_param_kinds.py`.
- Total repeated result: **70/70 browser-journey executions passed**.

One earlier full run against the first draft correctly failed the new
focus-survival assertion while both wire assertions passed. That exposed a
queued pointerup release clearing the new keyboard guard under suite load; the
final implementation separates pointer focus from keyboard focus and the five
required runs restart after that correction.

## Browser-free regression

- `./tools/run-tests.sh fast` — **196 tests passed**.

## Boundaries

This changes dashboard control focus/render behaviour and its browser
regression only. Verification used the real dashboard, headless Chromium, and
simfleet on loopback. No physical hardware, Pure Data, audio, touch/iPad, or
installation-LAN verification was performed or required for this keyboard
focus defect.
