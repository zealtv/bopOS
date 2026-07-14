# Distribution workflow results

Implemented a host-backed, fleet-wide patch workflow for managed simulation and
a device-reachable HTTP source for real-node distribution.

## Behaviour

- Managed Simulate mode lists every valid host patch through ordinary
  `/os/patches`; no fake `/os/fetch` or queued state is exposed.
- Switching from any virtual device selects one patch for the entire simulated
  fleet, reaps the old audition child (and its engine children), and launches a
  replacement with the selected manifest.
- Simulated UI hides Send/Sync/Add/Delete and explains that host patches are
  already available.
- Real-device Send derives the dashboard machine's routed LAN address when the
  browser was opened through loopback. `--public-url` remains authoritative;
  failure to find a route produces an actionable UI error before queue state is
  created.
- Live patch dropdown copy now states that it is device-reported installed
  inventory. Successful patch Send already triggers `/os/patches`, so the new
  patch appears there after its terminal receipt.

## Verification

- `verify_distribution_workflow.py`: **9/9 passed** — host inventory, fleet
  process replacement, active patch reporting, no phantom transfer, LAN URL
  derivation, explicit URL override, and UI/source semantics.
- `verify_distribution_ui.py`: **5/5 passed** in headless Chromium against the
  real dashboard and managed no-audio audition child — host dropdown, hidden
  distribution surface, switch to a second patch, and inventory after restart.
- Existing `verify_d8_simulation.py`: **9/9 passed**.
- Existing `verify_d8_sim_controls.py`: **9/9 passed**.
- Existing node distribution suite: every production-node assertion passed,
  including active-patch stop → fetch → restart → terminal ordering. Its one
  remaining failure is a stale sim-only assertion that requests
  `patch:default`; current `tools/simfleet.py` has initialized its active patch
  as `demo-pd` since later work. No simfleet source changed in this stitch.
- Existing dist-3 browser suite's HTTP/static checks passed, but its browser
  phase predates schema-1 seats and waits for an assigned row without creating
  a seat. The new focused browser suite covers the current seats UI.
- Python compilation, dashboard JavaScript syntax, and `git diff --check` pass.

## Hardware boundary

No command was sent to bop000 and no audible engine was launched. Bob will test
managed patch switching first, then real patch delivery and switching. No `.pd`
file changed.
