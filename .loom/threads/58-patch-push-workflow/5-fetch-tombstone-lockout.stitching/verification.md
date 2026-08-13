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

---

# Second pass verification (2026-08-13)

## Regression-first result

Four tests were added to `tests/test_fetch_generations.py` before any
implementation:

- `test_live_generation_stranded_by_reboot_does_not_lock_out_retry` — the
  reported Finn Jet defect, written from the observed wire behaviour;
- `test_stalled_generation_is_superseded_without_an_offline_edge` — the same
  recovery with no offline transition, and the negative case that a still
  progressing transfer is left alone and still coalesces;
- `test_progress_refreshes_the_stall_clock` — a slow multi-file transfer that
  keeps reporting is not superseded;
- `test_stranded_generation_still_bars_misattribution` — the first pass's
  invariant, re-asserted through the new path.

Starting-tree result: **7 tests, 4 failures/errors** (the three from the first
pass still passing). After implementation: **7 tests, 0 failures**.

## Required local checks

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile dashboard/osc_bridge.py dashboard/server.py \
  tests/test_fetch_generations.py
./tools/run-tests.sh fast
```

Compile passed; fast tier passed **331 tests, 0 failures** (327 before, plus
the 4 new).

## Live evidence that produced the reopening

Taken from Finn Jet before the fix, with the dashboard running `96bec64`:

- dashboard state held `fetch: {"patch:bonks-pd": "fetching"}`,
  `distribution: {}`;
- re-issuing `set_device_patch` over the websocket produced **no `/os/fetch`
  on the wire and no `ws_error`**; `journalctl -u bopos` on the device recorded
  nothing for the attempt across 100s of streamed `device_update` frames;
- `curl` of the manifest URL from the device returned `200` in 150ms, so the
  transport was healthy and the suppression was entirely dashboard-side.
