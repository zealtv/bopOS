# Verification

## Focused living tests

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m unittest -v \
  tests.test_manifest \
  tests.test_paramgen \
  tests.test_pointfield \
  tests.test_protocol_primitives
```

Result: **25 tests passed** in 0.010 seconds.

## Full fast tier

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  -m unittest discover -s tests -p 'test_*.py' -v
```

Result: **124 tests passed** in 0.162 seconds.

The expected negative-path logging from existing transport, shutdown, engine,
and node-log tests appeared; the suite result was `OK`.

## Compilation and hygiene

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile \
  tests/test_manifest.py \
  tests/test_paramgen.py \
  tests/test_pointfield.py \
  tests/test_protocol_primitives.py

git diff --check
```

Result: both passed.

## Boundaries

No Playwright suite was required because no browser or product behavior
changed. No archive guard was executed or modified. No hardware, LAN broadcast,
Pure Data, audible output, or iPad behavior was tested.
