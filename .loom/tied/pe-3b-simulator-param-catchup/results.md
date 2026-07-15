# pe-3b-simulator-param-catchup results

## Outcome

Fixed the silent `bonks-pd` simulator launch. Managed Pd processes can emit
their first heartbeat before the patch receive graph is ready, so the initial
parameter declaration response—and therefore the dashboard-owned `gain`
catch-up—could arrive too early and be lost.

The OSC bridge now retains the immediate fast path and schedules two bounded
parameter declaration replays at 1.5 and 4 seconds for a newly seen virtual
audition node. Replays are limited to the same device lifetime while the
simulate/edit supervisor remains active, and pending callbacks are cancelled
when the bridge closes.

## Verification

- Focused catch-up verifier: 6/6 passed.
- Existing simulation-toggle regression: 9/9 passed.
- Patch-editor PE-2 regression, including GUI Pd launch/cleanup: 27/27 passed.
- Python compilation and `git diff --check`: passed.
- Live audible gate: restarted the dashboard with the fixed code, launched
  `bonks-pd` through the normal simulator control, and Bob confirmed sound
  without any manual OSC gain injection.

The temporary diagnostic master value was restored from 0.5 to its prior 0.13.
No `.pd` file was edited.
