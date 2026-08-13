# Verification

## Regression-first result

Added `tests/test_fetch_generations.py` before the implementation and ran:

```sh
~/.venvs/bopos/bin/python tests/test_fetch_generations.py
```

Starting-tree result: **3 tests, 2 failures**. The failures showed that an
expired record still matched as in-flight and suppressed convergence emitted
no operator error.

After implementation, the same command passed: **3 tests, 0 failures**. It
proves that:

- an expired generation does not match or block a retry;
- the retry emits a second `/os/fetch` through the bridge send boundary;
- the first ambiguous terminal cannot certify the successor and causes a
  safety re-send;
- only the following terminal records the successor fingerprint;
- a genuinely active different generation still blocks; and
- convergence broadcasts an operator-visible error when a fetch cannot start.

## Required local checks

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile dashboard/osc_bridge.py dashboard/server.py \
  tests/test_fetch_generations.py
./tools/run-tests.sh fast
```

Result: compile passed; fast tier passed **327 tests, 0 failures**.

## Stronger integration attempt and boundaries

```sh
~/.venvs/bopos/bin/python tests/verify_device_patch_targeting.py
```

The existing real-dashboard + simfleet journey could not start Chromium in
this managed sandbox. Chromium exited at launch because macOS denied
`bootstrap_check_in` for its Mach rendezvous service (`Permission denied
(1100)`). No browser assertions ran, so this is recorded as an environment
boundary rather than a pass or product failure.

No physical device, LAN, audio engine, Pure Data, or hardware verification was
run. No `.pd` file was changed.
