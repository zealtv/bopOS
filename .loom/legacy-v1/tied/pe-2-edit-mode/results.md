# PE-2 verification record

Verified 2026-07-15 on macOS in the project venv.

## Focused gate

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/patch-editor/pe-2-edit-mode.stitching/verify_pe2_edit_mode.py
```

Result: **27/27 passed**. This drove the real dashboard in headless Chromium,
used the managed audition relay on non-default loopback ports, exercised edit /
simulate exclusivity and confirmation, default/master catch-up, live float and
checkbox delivery, closed-engine/relaunch/restart behavior, fleet-control
isolation, text-input focus, stale-write avoidance, spawn-failure rollback,
and patch retargeting.

The same verifier found the installed Pd 0.55-2 application and performed the
required real GUI-PD launch with `patches/demo-pd`: one edit device reported a
live engine. Teardown reaped the audition process, Pd GUI, and watchdog; a
post-run process check found none remaining. No `.pd` file was changed.

Static checks passed for all touched Python, JavaScript, and whitespace:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  tools/audition.py dashboard/server.py dashboard/osc_bridge.py \
  .loom/threads/patch-editor/pe-2-edit-mode.stitching/verify_pe2_edit_mode.py
node --check dashboard/static/js/dashboard.js
git diff --check
```

## Adjacent regressions

- `d8-2-simulate-toggle/verify_d8_simulation.py`: **9/9 passed**
- `d8-4-sim-controls/verify_d8_sim_controls.py`: **9/9 passed**
- `fp-3b-patch-param-reset/verify_fp3b_param_reset.py`: **9/9 passed**
- `boundary-5-launch-context-and-topology/verify_launch_context.py`: **68/68 passed**

Two older historical audition verifies were also inspected. They fail on
already-superseded expectations: `audition-1a` expects the retired startup
`ID` token and assumes every captured report is `/hb`; `audition-1c` imports
that same old no-ready-frame assertion. PE-2 intentionally adds the private
`/audition/ready ... edit` mode frame, while the current launch-context suite
confirms the ratified startup surface. The tied historical artifacts were not
rewritten.

## Boundary

This is a macOS laptop/dashboard gate. No Pi deployment was required, and no
claim is made here about iPad/touch layout; the interactive UI audit remains
scheduled for `ui-tabs/tabs-2-review-session` after `pe-3`, `pe-4`, tabs-0
ratification, and tabs-1.
