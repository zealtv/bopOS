# Verification

## Focused living tests

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m unittest -v \
  tests.test_mute_safety \
  tests.test_device_enabled \
  tests.test_device_control_routing \
  tests.test_audition_output_gate \
  tests.test_audio_config
```

Result: **31 tests passed** in 0.032 seconds on the final rerun.

## Full fast tier

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  -m unittest discover -s tests -p 'test_*.py'
```

Result: **144 tests passed** in 0.179 seconds on the final rerun.

Expected negative-path logging from transport, shutdown, engine, and node-log
tests appeared; the suite result was `OK`.

## Compilation and hygiene

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile \
  tests/test_mute_safety.py \
  tests/test_device_control_routing.py \
  tests/test_audio_config.py

git diff --check
```

Result: both passed.

## Honest boundary

These software tests establish state composition, protocol convergence,
restart reapplication, mixer-target selection, failure behavior, and simfleet
parity. Mocked `amixer` calls cannot prove that a real board's selected control
silences its DAC, that no transient sound escapes during boot or restart, or
that the remembered ALSA target remains valid after hardware changes. No
Playwright, Raspberry Pi, Pure Data, audible-output, LAN, or iPad check was run.
