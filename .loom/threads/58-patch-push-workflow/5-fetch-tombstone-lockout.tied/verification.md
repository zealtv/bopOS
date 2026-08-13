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

## Hardware verification — Finn Jet, 2026-08-13

Unlike the first pass, this one was verified on the rig. Bob restarted the
dashboard onto the fix; everything below is the real device over the LAN.

Push of `bonks-pd` to Finn Jet, streamed from the websocket:

```
[  0.0] fetch={'patch:bonks-pd': 'sent'}
[  0.1] fetch={'patch:bonks-pd': 'fetching'}
[  0.8] fetch={'patch:bonks-pd': 'ok'}   dist={'patch:bonks-pd': '0977f38f…'}
[  5.0] switch status 'reconciling'  ->  cleared
```

Device side:

```
FETCH http://192.168.0.100:8080/patches/bonks-pd/.manifest.json
      patch:bonks-pd: ok (fetched 3 files)
ACTIVE PATCH: bonks-pd
Patch switch complete: bonks-pd
```

The delivered manifest carries 8 `kind` entries and no `cues`, replacing the
2026-07-25 copy that still used the retired `type`/`min`/`max` grammar.

Round trip repeated to prove it was not a one-off unblocking:
`bonks-pd -> demo-pd -> bonks-pd`, each switch completing in about 4s, with
the device up continuously (`up 32 min`) and SSH responsive throughout.

## Not verified

The **SSH freeze** Bob reported during a failed switch was not reproduced and
is not explained. It could not be: persistent journald is off on this node, so
only the current boot is retained and the episode's logs were gone. The
plausible mechanism — `bopos.py:1858-1877` rolls a failed switch back by
running two full jackd+Pd teardown/startup cycles, jackd at realtime priority
70, with waits of up to 60s for ALSA and 15s for jack, on a node with 415MB
RAM — is inference from the code, not measurement. Recorded so nobody reads
this stitch as having closed it. Enabling `Storage=persistent` in journald on
the rig nodes would make the next occurrence diagnosable.

No `.pd` file was changed.
