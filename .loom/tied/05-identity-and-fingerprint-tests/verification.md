# Verification

## Focused living tests

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m unittest -v \
  tests.test_identity_fingerprint \
  tests.test_device_patch_override \
  tests.test_asset_slot_context \
  tests.test_node_fetch_dispatch \
  tests.test_osc_transport
```

Result: **39 tests passed** in 0.092 seconds.

The malformed asset fact emitted its expected quarantine warning. Existing
negative-path shutdown and OSC transport logs also appeared; the result was
`OK`.

## Full fast tier

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  -m unittest discover -s tests -p 'test_*.py'
```

Result: **154 tests passed** in 0.218 seconds.

Expected negative-path logging from inventory quarantine, transport, shutdown,
engine, and node-log tests appeared; the suite result was `OK`.

## Compilation and hygiene

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile \
  dashboard/osc_bridge.py \
  tests/test_identity_fingerprint.py

git diff --check
```

Result: both passed.

## Honest boundary

These software tests establish state precedence, canonical hashing, cache
invalidation, inventory ingestion, derived drift reporting, and simulator
parity. They do not prove that a deployed node discovers the intended physical
interface MAC on a particular network topology, that UDP inventory replies
arrive over the installation LAN, or that filesystem stat/cache behavior on a
Pi SD card matches the development host under load. No Playwright, Raspberry
Pi, Pure Data, audible-output, LAN, or iPad check was run.
