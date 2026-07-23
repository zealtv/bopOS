# Output gate follow-up — results

Finn Jet's physical Device control was working at `5eda7b4`.

- The node received and acknowledged disable with `device_enabled=false` and
  `output_enabled=false`; it became inaudible.
- A direct Enable through the same Dashboard path was acknowledged with both
  fields true and restored audio.
- A fresh browser rendered `Disable` / `enabled` correctly. The apparently
  stuck control was an old open page retained across the application update;
  Bob confirmed enable/disable worked after a hard refresh.

The genuine code defect was audition MUTE ALL. The relay recorded `mute_all`
but deliberately sent nothing to its engines. Audition now composes the
execution output gate through the already-provided `/os/master` engine surface:

- MUTE ALL sends effective master `0`;
- master changes while muted are retained but remain effectively `0`;
- resume restores the latest requested master;
- `/os/mute` remains hidden from engines;
- selectors still affect only their matching virtual nodes.

No production physical route, wire grammar, port, or `.pd` file changed.

## Verification

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m unittest discover -s tests -p 'test_*.py'
# 30/30 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_device_control_modes.py
# 13/13 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile tools/audition.py tests/test_audition_output_gate.py \
  tests/verify_device_control_modes.py

git diff --check
```

All checks passed. The browser integration used isolated local audition and
fake-physical UDP receivers. Simulation's engine-facing gate was captured
directly; audible Simulation behavior remains for Bob's local audio check after
restarting the managed Simulation process.
