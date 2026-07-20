# Verification results

Verified on macOS (Darwin), 2026-07-20.

## Passing checks

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile tools/audition.py \
  .loom/threads/audition-automation-parity/aa-2-audible-simulation-gate/aa-1-audition-generator-parity.stitching/verify_audition_automation.py
```

Passed with no output.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/audition-automation-parity/aa-2-audible-simulation-gate/aa-1-audition-generator-parity.stitching/verify_audition_automation.py
```

Passed 12/12 checks using the real audition command loop, loopback OSC, and
three fake engine UDP receivers. This covers byte-equivalent scalar relay,
fade/LFO expansion, exact Seat/Group/All selection, independent node slots,
aligned non-free phase, stop/plain replacement, integer crossings, malformed
grammar recovery, nested identities, passthrough behavior, and deterministic
worker shutdown.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/automation-1-engine-and-parity/verify_param_automation.py
```

Passed with 0 failures (32 shared parser, scheduler, and simfleet checks).

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/pe-3b-simulator-param-catchup/verify_sim_param_catchup.py
```

Passed 6/6 checks.

The older `d8-2-simulate-toggle` suite passed all eight managed-process,
virtual-device, retarget, teardown, and persistence checks relevant here. Its
only failure was the stale UI-source assertion `sidebar exposes managed
Simulate mode` after that control moved in later dashboard work.

The newer `01-simulation-transition-coherence` suite passed both backend
checks (rejecting a queued update for a removed virtual UID, and restoring the
Live assignment/master/mute target). Its browser phase timed out waiting for
the retired `#cards .card` live-view locator before exercising transitions.

## Historical baseline limitations

Two early Stage-0 verifier entrypoints no longer run to completion against the
current launch contract:

- `audition-1a-relay-launcher/verify_audition.py` expects the retired `ID N`
  Pd startup token; current launch context has delivered identity on `/id`
  since the engine-boundary work.
- `audition-1c-engine-boundary-adoption/verify_audition_boundary.py` constructs
  an old two-field run-context fixture without the now-required `version` and
  `patch_fingerprint` fields.

These failures occur in unchanged launch-context assertions outside the new
parameter relay and were not hidden by modifying tied evidence.

## Boundary

This stitch proves relay parsing, scheduling, selector behavior, and the exact
datagrams delivered to fake engine ports. It does **not** prove human
audibility, CoreAudio output, Dashboard marker/thumb agreement by eye, or a
real Pd engine. Those belong to parent stitch `aa-2-audible-simulation-gate`.
No `.pd` file was edited and no Pd-side work was identified.
