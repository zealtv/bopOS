# Verification

## Focused runner contract

```sh
chmod +x tools/run-tests.sh
bash -n tools/run-tests.sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  -m unittest -v tests.test_test_runner
```

Result: shell syntax passed and **5 tests passed** in 1.124 seconds.

The focused tests include deliberate fake fast/browser failures and confirm
the runner continues, summarizes every browser surface, and exits nonzero.

## Real fast tier through the new entry point

```sh
./tools/run-tests.sh fast
```

Result: **182 tests passed** in 0.800 seconds.

Expected negative-path logging from admin, inventory quarantine, transport,
shutdown, engine, and node-log tests appeared; the suite result was `OK`.

## Real browser tier through the new entry point

```sh
./tools/run-tests.sh browser
```

Result: **12 of 12 verifier files passed** in fresh processes. The final
summary reported `PASS` for every living `tests/verify_*.py` surface:

- Control surface component and Control tab
- Device control modes and Device control panel
- Device patch targeting and Set-patch handoff
- Generator drawer and live checkbox/slider commits
- Log destination and OSC transport monitor
- Manifest parameter visibility
- Precision parameter input

The first sandboxed attempt was denied local socket/route access and correctly
continued to a 12-file FAIL summary. Re-running with local network permission
allowed the actual loopback browser journeys to complete green.

## Static, documentation, and CI checks

```sh
bash -n tools/run-tests.sh

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile tests/test_test_runner.py

git diff --check
test ! -d .github
rg -n './tools/run-tests\.sh|\.loom/tied|BOPOS_PYTHON|hardware|iPad' \
  docs/VERIFICATION.md tools/run-tests.sh
```

Result: all passed. No repository CI surface exists.

## Honest boundary

Fast and browser software tiers are green. No Raspberry Pi, Pure Data,
audible-output, physical LAN, peripheral, reboot, persistent-node, or iPad
check was run. Browser journeys used headless Chromium and local simulated
peers; they do not establish hardware adoption.
