# Verification

## Focused living tests

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m unittest -v \
  tests.test_fetcher \
  tests.test_node_fetch_dispatch \
  tests.test_simfleet_fetch
```

Result: **13 tests passed** in 0.015 seconds.

A final non-verbose rerun after adding the explicit during-fetch responsiveness
assertion also passed 13 tests in 0.012 seconds.

## Full fast tier

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  -m unittest discover -s tests -p 'test_*.py'
```

Result: **135 tests passed** in 0.168 seconds on the final rerun.

Existing negative-path logging from transport, shutdown, engine, and node-log
tests appeared as expected; the suite result was `OK`.

## Compilation and hygiene

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile \
  tests/test_fetcher.py \
  tests/test_node_fetch_dispatch.py \
  tests/test_simfleet_fetch.py

git diff --check
```

Result: both passed.

## Honest boundary

These software tests establish validated byte replacement, queue/progress
ordering, asynchronous dispatcher responsiveness, and simulator parity. They
do not reproduce a fresh Pi's cold cache, first real HTTP transfer, SD-card or
Wi-Fi stalls, process scheduling, engine audio, or timeout behavior. No
Playwright, hardware, Pure Data, audible, LAN, or iPad check was run.
