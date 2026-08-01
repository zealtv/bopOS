# spinner readiness race fix

The spinner could remain forever when the local WebSocket delivered its first
`state` before the long page script reached `ws.on("state", ...)`. The shared
`BopSocket` now queues events that arrive without a registered handler and
drains them, in order, when the first handler registers. This also preserves an
early connection event. Normal post-registration delivery is unchanged.

Both spinner captions now read `loading...`.

## Verification

Passed 2026-07-20:

```text
node --check dashboard/static/js/ws.js
node .loom/threads/dashboard-loading-spinner-ready-fix.stitching/verify_ready_race.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/dashboard-loading-spinner-ready-fix.stitching/verify_spinner_regression.py
git diff --check
```

The deterministic Node regression delivered connection and state synchronously
inside socket setup, before handler registration, and proved both were later
received. The copied real-server + simfleet Playwright regression passed all
13 original spinner checks on both pages, including dismissal, steady-state
absence, reduced motion, and no console errors. `review-spinner.png` retains
the updated caption.

Bob's untracked `dashboard/shows/` working material was untouched.
