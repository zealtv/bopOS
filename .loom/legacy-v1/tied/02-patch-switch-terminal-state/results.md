# Patch-switch terminal-state results

## Outcome

- Patch switches now use explicit runtime attempts: `switching` becomes
  `reconciling`, then observation either clears the attempt as success or the
  bounded monitor records `failed` / `timeout` with an operator-facing reason.
- `/os/rev` starts reconciliation instead of assuming success. `/os/patches`
  and `/os/report` can prove success after a lost/unattributable receipt; late
  contrary observation upgrades timeout to failure.
- Attempt object identity prevents an older monitor from changing a newer
  Retry. A new fleet generation invalidates prior attempt tokens.
- Devices renders distinct **switch failed** and **switch timed out** badges,
  the attempt reason, and a one-device **Retry** action.

## Verification

Passed:

```sh
node --check dashboard/static/js/dashboard.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile dashboard/server.py dashboard/state.py dashboard/osc_bridge.py .loom/threads/ui-tabs/tabs-3-next-sweep/02-patch-switch-terminal-state.stitching/verify_patch_switch_terminal.py .loom/threads/ui-tabs/tabs-3-next-sweep/02-patch-switch-terminal-state.stitching/verify_patch_switch_terminal_ui.py
```

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/threads/ui-tabs/tabs-3-next-sweep/02-patch-switch-terminal-state.stitching/verify_patch_switch_terminal.py
```

Result: **12/12 passed** — normal receipt, lost receipt, observed failure,
no-observation timeout, late success/failure, one-device Retry, and fleet
generation supersession.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/threads/ui-tabs/tabs-3-next-sweep/02-patch-switch-terminal-state.stitching/verify_patch_switch_terminal_ui.py
```

Result: **5/5 passed** in headless Chromium against the real dashboard —
current Devices workspace labels/reasons, Retry dispatch, and clean shutdown.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/tied/tabs-1-skeleton/verify_tabs_skeleton.py
```

Result: **20/20 passed** — current tab shell and relocated controls.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/tied/fp-2-fleet-state/verify_fp2_fleet_state.py
```

Result: **25 behavioral checks passed; 1 obsolete source assertion failed**.
The assertion requires `ws.send("switch_patch"` in `dashboard.js`; FP-3 removed
that legacy per-device/simulation UI path in favour of the global
`set_fleet_patch` workflow. Real simfleet discovery, Set, convergence, Retry,
overlap ownership, second choice, and Revert all passed.

`git diff --check` passed.

## Boundaries

No `.pd` file changed. Verification used simulated nodes and headless Chromium;
no hardware rig, audible engine, installation LAN, or iPad/touch browser was
tested.
