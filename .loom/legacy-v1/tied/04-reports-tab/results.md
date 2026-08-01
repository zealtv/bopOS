# 04-reports-tab results

## Outcome

- Added the ratified Monitor Reports tab with assigned physical Device target,
  report-name input, one-shot Request action, session history, typed values,
  receipt time, and explicit timeout/error states.
- Unassigned and offline Devices remain visible but unavailable.
- Added a bounded backend `/os/probe` request correlator. It retains no report
  values in Dashboard state and creates no subscription or polling loop.
- Requests use the physical installation route and both request/reply remain
  visible in Outgoing/Incoming.
- The UI explains the real semantics of `to-bopos-report`: latest value in node
  memory, cleared by node restart.

## Verification

```text
node --check dashboard/static/js/monitor.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/test_monitor_probe.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/20-console-dock/04-reports-tab.stitching/verify_monitor_reports.py
git diff --check
```

Results: **2/2 living bridge tests** and **7/7 real-server + simfleet
Playwright checks** passed, covering typed replies, assigned routing,
unassigned exclusion, raw traffic visibility, unknown-name timeout, and no
browser errors.

The simulated node's contract-held `version` report supplies the browser
journey. The living bridge test supplies mixed patch-authored `i`/`f`/`s`
values because simfleet deliberately has no per-node localhost 7770 engine
socket.
