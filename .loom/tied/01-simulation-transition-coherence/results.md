# Simulation transition coherence results

## Outcome

- Device-scoped broadcasts now resolve only from the current runtime registry
  and recheck object identity after asynchronous catalog enrichment. Queued or
  in-flight updates cannot recreate a removed/replaced virtual uid.
- Every managed-audition exit path restores the performance OSC target and
  replays live seat assignments, master, and mute.
- The focused browser regression drives the real dashboard and managed
  audition runtime rapidly through Simulation -> Live and Patch edit -> Live.
  Virtual cards clear without refresh while the bound live card and dashboard
  control state remain intact.

## Verification

Passed:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile dashboard/server.py .loom/threads/ui-tabs/tabs-3-next-sweep/01-simulation-transition-coherence.stitching/verify_simulation_transition.py
```

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/threads/ui-tabs/tabs-3-next-sweep/01-simulation-transition-coherence.stitching/verify_simulation_transition.py
```

Result: 7/7 passed. This includes a forced deletion while `broadcast()` is
awaiting device enrichment, exact live OSC target/assignment/master/mute replay,
and headless Chromium against the real dashboard plus no-engine managed audition
subprocess.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/tied/d8-2-simulate-toggle/verify_d8_simulation.py
```

Result: 9/9 passed.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/tied/pe-3b-simulator-param-catchup/verify_sim_param_catchup.py
```

Result: 6/6 passed.

```sh
git diff --check
```

Result: passed.

## Boundaries

No `.pd` file changed. The managed runtime used `--sim-no-engine`; no audible
engine, hardware rig, iPad/touch browser, or real installation LAN was tested.
