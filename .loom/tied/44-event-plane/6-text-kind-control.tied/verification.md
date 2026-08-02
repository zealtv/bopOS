# Verification

## Passed

```sh
~/.venvs/bopos/bin/python tests/test_css_component_ownership.py
# 5 tests, OK

~/.venvs/bopos/bin/python tests/test_dom_event_handlers.py
# 1 test, OK

node --check dashboard/static/js/control-surface.js
~/.venvs/bopos/bin/python -m py_compile tests/verify_control_surface_component.py
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
  git -c core.excludesFile=/dev/null diff --check

./tools/run-tests.sh fast
# 288 tests, OK
```

The living control-surface journey now covers the text row's render and
height, component-owned face, mixed hatch/placeholder, absence of a generator,
Enter and blur sends through the real dashboard + simfleet, and preservation
of a focused draft across a heartbeat re-render.

## Browser boundary

The focused journey was invoked:

```sh
~/.venvs/bopos/bin/python tests/verify_control_surface_component.py
```

It could not start Chromium in this managed workspace. Chromium exited before
loading the app with macOS Mach-port sandbox denial:

```text
bootstrap_check_in org.chromium.Chromium.MachPortRendezvousServer: Permission denied
```

Accordingly, the new Playwright assertions are present but are **not claimed
as passed in this session**. No real browser interaction, iPad/touch, hardware,
Pure Data, or audible verification was performed.
