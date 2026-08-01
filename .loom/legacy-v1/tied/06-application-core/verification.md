# Verification — 06-application-core

Date: 2026-07-29.

## Focused

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile dashboard/preset_application.py dashboard/preset_store.py \
  dashboard/osc_bridge.py dashboard/state.py dashboard/server.py \
  tests/test_preset_application.py
```

PASS.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/test_preset_application.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/test_preset_store.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/test_paramgen.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/test_device_control_routing.py
```

PASS: 7 + 10 + 5 + 6 = 28 tests.

Coverage includes:

- drift clamping and dropped identities;
- effective-patch mismatch skip and per-Seat fallback;
- `all`/`gN` coalescing only when every concrete Seat survives;
- timed float/int fades and toggle/enum/text/generator snap behavior;
- one persist and one application report;
- persist-failure rollback with no OSC send or broadcast;
- canonical float round trip and integer flooring;
- active LFO/loop replay with unchanged `sent_at`;
- expired fade replay through its durable scalar;
- stop-time fade evaluation and canonical durable device/Seat mirrors;
- aggregate capture with mixed omission;
- per-Seat provenance, agree-or-mixed projection, derived dirtiness, and
  lowest-group-id target tie-break;
- provenance exclusion from durable installation state.

The server import was also checked from `/tmp`, outside the repository working
directory. `git diff --check` passed.

## Repository tier

```sh
./tools/run-tests.sh fast
```

PASS: 218 tests.

## Boundary

This stitch adds no browser UI, so no Playwright journey was required. OSC
address/argument fan-out was verified against the real bridge recording logic
with an isolated transport; no physical node, Pure Data receiver, installation
LAN, audible result, or iPad interaction was exercised. Free LFO and
`sh`/`drift` Stop values are intentionally dashboard-state estimates, not
observations of engine output.
