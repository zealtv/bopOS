# Results

Completed the real-dashboard integration and product-copy verification for
physical-device aliases.

## Behaviour verified

- A physical device discovered after the browser WebSocket opens now converges
  its newly allocated durable registry entry into the browser. The verifier
  exposed this missing convergence edge; `dashboard/osc_bridge.py` now emits a
  full state update once when an alias is allocated.
- The Devices roster, Seats picker and binding note, Assets target selector,
  and embedded Dashboard card use the alias as their only physical-device
  identity. Hostname and full UID/MAC remain together in the selected Device
  detail.
- Rename, case-insensitive duplicate rejection, Reset, venue-load isolation,
  dashboard-process restart, real offline transition, and genuine durable
  Forget are covered through the real server, simulator, WebSocket and browser.
- Rename, Reset and the alias input remain visible, at least 44 px high, and
  free of page overflow at a 375 x 812 viewport.
- Generator v1's complete 64 x 64 vocabulary is linted. The retained
  `word-list-review.md` records every token and the exact scope of Bob's human
  language direction without claiming line-by-line human approval.

## Verification evidence

Commands were run from the repository root with
`PYTHONPYCACHEPREFIX=/tmp/bopos-pycache` and the project venv.

- `verify_device_alias_browser.py`: **18/18 passed**.
- `verify_device_alias_wordlists.py`: **9/9 passed**.
- `verify_identity_visibility.py`: **6/6 passed**.
- `.loom/tied/01-registry-and-generator/verify_device_alias_registry.py`:
  **16/16 passed**.
- `.loom/tied/07-seats-workspace/verify_seats_workspace_browser.py`:
  **12/12 passed**.
- `.loom/tied/11b-single-device-assets-workspace/verify_single_device_assets_workspace.py`:
  **17/17 passed**.
- `.loom/tied/2-dashboard-state-editor/verify_param_dashboard_browser.py`:
  **12 checks passed, 0 failures**.
- Python compilation passed for `dashboard/osc_bridge.py` and both new focused
  verifier scripts.

The tied Seats and Assets regressions regenerate retained screenshots. Those
four tied images were restored after the run; this stitch does not alter prior
evidence.

## Superseded or stale regressions

- `.loom/tied/02-editing-and-cross-surface-ui/verify_alias_ui_browser.py`
  reached the real generated-alias UI, then failed its old requirement that a
  UID tail remain in the roster. Bob's later selected-detail-only technical
  identity ruling intentionally supersedes that assertion. The new 18-check
  suite replaces its alias hierarchy coverage without editing the tied file.
- `.loom/tied/02-editing-and-cross-surface-ui/verify_alias_ui_backend.py` has
  the corresponding obsolete `Identity.full(...)` / technical-identity source
  expectations and is likewise superseded by the new static and browser
  guards.
- `.loom/tied/09-devices-workspace/verify_devices_workspace.py` passed its
  first **8** workspace checks, then stopped on a stale literal expectation of
  report contract version `1.5`; the simulator correctly reports the ratified
  current `1.6`. The failure occurred before later checks and is unrelated to
  alias behaviour. The new suite directly covers Devices identity, editing,
  restart, offline and Forget behaviour.

## Boundaries

- No real Raspberry Pi or installation LAN was used. Physical MAC discovery,
  real-node restart/offline timing and hardware Forget/reappearance remain rig
  adoption checks.
- Chromium at desktop and 375 px widths was exercised. Safari/iPad touch,
  screen-reader announcements, pronunciation across the complete vocabulary,
  and colour/contrast audits were not independently tested.
- No Pure Data files were changed and no audible behaviour is asserted.
