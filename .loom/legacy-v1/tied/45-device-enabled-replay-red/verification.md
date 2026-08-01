# Verification

## Focused safety tests

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -m unittest -v \
  tests.test_device_control_routing tests.test_device_enabled tests.test_mute_safety
```

Result: 20 tests passed.

Each module also passed independently: 6 device-control routing tests, 7
device-enabled tests, and 7 mute-safety tests.

## Accordion browser journey

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  tests/verify_control_surface_component.py
```

Result: all 45 checks passed, including the 9 accordion structure,
interaction, and persistence checks. No facilitator or dashboard page errors.

## Static and full fast tier

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile tests/test_device_control_routing.py
./tools/run-tests.sh fast
git diff --check
```

Result: compile and diff checks passed; the canonical fast tier passed all 184
tests. Expected negative-path transport and shutdown logging appeared.

## Honest boundary

No Raspberry Pi, installation-LAN, Pure Data, audible-output, iPad, or touch
check was run. The device replay result is a deterministic OSC unit regression;
the accordion result is headless Chromium desktop interaction.
