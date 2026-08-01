# fp-3b verification

## Result

Managed simulation and deployed fleet staging now treat a patch-name change as
a parameter-schema change. Every seat is replaced with exactly the new
manifest defaults, runtime device mirrors are reset before convergence, and a
durable `params_patch` marker repairs pre-migration installations once. A
same-name Set or Retry preserves operator values; Revert applies the previous
manifest defaults.

No `.pd` files were edited.

## Commands

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/server.py dashboard/state.py \
  .loom/threads/fleet-patch/fp-3b-patch-param-reset.stitching/verify_fp3b_param_reset.py
git diff --check
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/fleet-patch/fp-3b-patch-param-reset.stitching/verify_fp3b_param_reset.py
```

Focused browser-free managed-audition verification: **9/9 passed**.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/fp-3-fleet-ui/verify_fp3_fleet_ui.py
```

Fleet UI regression: **13/13 passed**.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/d8-2-simulate-toggle/verify_d8_simulation.py
node --check dashboard/static/js/dashboard.js
```

Simulation regression: **9/9 passed**. JavaScript syntax check passed.

## Boundary

Verification used managed audition with `--no-engine`; it did not assert
audible Pure Data output, real-node convergence, LAN behavior, or iPad/touch
interaction. The original failure was reproduced diagnostically: `bonks-pd`
launched, while durable zero-valued `gain` parameters overrode its manifest
default. The focused test covers that state migration and restart path without
requiring a `.pd` change.
