# dashboard loading spinner completion notes

Both Dashboard entry points now render a full-viewport loading treatment from
their initial HTML and themed CSS. Four bop-palette bars move in a staggered,
rhythmic beat; `prefers-reduced-motion` renders the same mark statically.

The technical and facilitator state handlers hide the overlay only after the
first WebSocket `state` has been applied and rendered. The node remains hidden
for the rest of that document's lifetime, so reconnect behavior stays with the
existing status indicators.

## Verification

Passed 2026-07-20:

```text
node --check dashboard/static/js/dashboard.js
node --check dashboard/static/js/facilitator.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  .loom/threads/dashboard-loading-spinner.stitching/verify_loading_spinner.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/dashboard-loading-spinner.stitching/verify_loading_spinner.py
git diff --check
```

The focused real-server + simfleet Playwright verifier passed 13 checks. It
intercepted and delayed the first WebSocket state independently on both pages,
proved the overlay preceded state, covered the viewport, animated, disappeared
after release/application, stayed absent in steady state, emitted no console
errors, and had a static reduced-motion treatment. `review-spinner.png` is the
retained review frame.

No hardware, physical iPad, or touch test was performed. Bob's untracked
`dashboard/shows/` working material was untouched.
