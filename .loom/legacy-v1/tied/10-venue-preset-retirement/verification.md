# Verification — 10-venue-preset-retirement

Date: 2026-07-29.

## Static and focused checks

- `rg -n 'save_preset|load_preset|preset_scope_seats' python dashboard tools
  tests docs` — no matches.
- `node --check dashboard/static/js/dashboard.js` — PASS.
- `node --check dashboard/static/js/facilitator.js` — PASS.
- `python -m py_compile` on `dashboard/state.py`, `dashboard/server.py`,
  `tests/test_venue_preset_retirement.py`,
  `tests/test_preset_application.py`, and `tests/verify_control_tab.py` —
  PASS.
- `tests/test_venue_preset_retirement.py` — PASS, 3 tests. Covers loading and
  resaving an old installation, Seat reindex/delete after legacy adoption,
  and loading/resaving an old venue snapshot.
- `tests/test_preset_application.py` — PASS, 22 tests. Confirms the replacement
  patch-preset application core remains green.
- `tests/verify_control_tab.py` — PASS, 22 checks. Confirms the desktop
  patch-preset row remains, the venue shelf is absent, and the standalone
  facilitator has no preset affordance or page errors.
- `git diff --check` — PASS.

All Python commands used `~/.venvs/bopos/bin/python`; compile used
`PYTHONPYCACHEPREFIX=/tmp/bopos-pycache`.

## Repository suite

`./tools/run-tests.sh all`, rerun with permission to bind loopback TCP/UDP
ports:

- browser-free — PASS, 248 tests;
- browser — 16 of 17 journeys PASS;
- the only red journey is `verify_generator_drawer.py`, whose agreeing and
  mixed Stop checks both observe simfleet ticks continuing after dashboard
  automation clears (`20 → 110 → 172` and `20 → 111 → 172`).

That exact failure was reproduced before Show preset messages and is already
the second item in `11-browser-test-failures`. Stitch `11` explicitly depends
on this retirement tying first. The changed Control journey, standalone
facilitator boundary, patch-preset Control/Device/editor journeys, Show
reference journey, and every browser-free test pass.

## Boundaries

Nothing in this removal is hardware-gated. It changes host persistence,
host-side websocket dispatch, HTML/CSS/JavaScript surfaces, tests, and
operator documentation only. No Pure Data, audible, physical-device,
installation-LAN, or iPad hardware check is required to establish the removed
surface; the standalone responsive browser path was exercised in Chromium.
