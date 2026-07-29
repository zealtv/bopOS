# Verification — 05-store-and-foundations

Date: 2026-07-29.

## Focused

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile python/manifest.py python/identity.py python/fetcher.py \
  dashboard/server.py dashboard/preset_store.py tests/test_manifest.py \
  tests/test_identity_fingerprint.py tests/test_fetcher.py \
  tests/test_preset_store.py
```

PASS.

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_manifest.py
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_fetcher.py
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_identity_fingerprint.py
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/test_preset_store.py
```

PASS: 12 + 9 + 11 + 10 = 42 tests.

Coverage includes:

- toggle validate → atomic save → validate round trip;
- preset add/edit/delete leaving the patch fingerprint unchanged;
- stale host-only hash-cache entry removal;
- patch convergence preserving destination presets while pruning ordinary
  stale files;
- `file://` convergence excluding source presets;
- symlink rejection remaining active inside a preserved presets directory;
- mounted FastAPI/Starlette `/patches` requests returning 404 for preset
  paths;
- strict file shape and full-state entry validation;
- invalid-file list/read/delete behavior;
- atomic CRUD, revision CAS, slug collisions and external cache invalidation;
- canonical schema projection, ordered enum-label sensitivity, and the
  apply/clamp/drop drift matrix.

`git diff --check` PASS.

## Repository tier

```sh
./tools/run-tests.sh fast
```

PASS: 211 tests.

## Boundary

No browser journey is required: this stitch adds no browser UI or WebSocket
verb. No physical node, Pure Data, installation LAN, audible output or iPad
behavior was exercised. The transfer behavior was verified with the real
`file://` fetcher and temporary patch roots; HTTP denial was verified through
an in-process mounted ASGI application.
