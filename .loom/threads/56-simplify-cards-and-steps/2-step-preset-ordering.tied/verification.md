# Verification

## Regression-first evidence

Before implementation:

```sh
~/.venvs/bopos/bin/python -m unittest \
  tests.test_show_model.ShowPlaybackOrderingTests \
  tests.test_preset_application.PresetApplicationTests.test_fade_takeover_origin_matches_node_live_value
```

Failed in all three defective cases: the late preset overwrote the following
parameter (`0.25 != 0.9`), the mid-fade mirror used the old destination
(`1.0 != 0.4`), and the mid-LFO mirror used the pre-generator scalar
(`0.2 != 0.5`).

## Passing verification

```sh
~/.venvs/bopos/bin/python -m unittest \
  tests.test_show_model.ShowPlaybackOrderingTests \
  tests.test_preset_application.PresetApplicationTests.test_fade_takeover_origin_matches_node_live_value
```

2 tests passed.

```sh
~/.venvs/bopos/bin/python -m unittest \
  tests.test_show_model tests.test_preset_application
```

48 tests passed.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile dashboard/show_engine.py dashboard/osc_bridge.py \
  tests/test_show_model.py tests/test_preset_application.py
```

Passed.

```sh
./tools/run-tests.sh fast
```

266 tests passed.

## Boundaries

No browser, hardware, real-LAN, audio, or Pure Data verification was run. The
change is confined to browser-free Show playback ordering and dashboard mirror
logic; the repository verification matrix requires the fast tier for these
surfaces.
