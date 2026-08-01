# Verification

## Focused living tests

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m unittest -v \
  tests.test_show_model \
  tests.test_group_membership \
  tests.test_sync_protocol \
  tests.test_admin_outcomes \
  tests.test_protocol_primitives \
  tests.test_monitor_send
```

Result: **34 tests passed** in 0.046 seconds on the final rerun.

The deliberate callback-exception case emitted its expected warning; the
result was `OK`.

## Full fast tier

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  -m unittest discover -s tests -p 'test_*.py'
```

Result: **177 tests passed** in 0.259 seconds on the final rerun.

Expected negative-path logging from admin, inventory quarantine, transport,
shutdown, engine, and node-log tests appeared; the suite result was `OK`.

## Compilation and hygiene

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile \
  tests/test_show_model.py \
  tests/test_group_membership.py \
  tests/test_sync_protocol.py \
  tests/test_admin_outcomes.py

git diff --check
```

Result: both passed.

## Honest boundary

The fast software tier establishes schema/persistence behavior, group
transactions, sync estimator/scheduler policy, and update receipt ordering. A
local scheduler thread verifies ordering with a generous deadline; it is not a
jitter measurement. The tests do not establish real websocket/browser Show
editing, UDP behavior on the installation LAN, Wi-Fi asymmetry, clock quality,
Pi scheduling, GPIO/audio cue timing, system authorization, reboot/reappearance,
or unattended Git convergence on a persistent node. No Playwright, Raspberry
Pi, Pure Data, audible-output, real-LAN, or iPad check was run.
