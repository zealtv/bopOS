# Verification

## Passed

```sh
~/.venvs/bopos/bin/python tests/test_remote_verb_promotion.py
# 6 tests, OK

~/.venvs/bopos/bin/python tests/test_css_component_ownership.py
# 5 tests, OK

node --check dashboard/static/js/dashboard.js
~/.venvs/bopos/bin/python -m py_compile \
  dashboard/state.py dashboard/server.py \
  tests/test_remote_verb_promotion.py \
  tests/verify_manifest_param_visibility.py

./tools/run-tests.sh fast
# 294 tests, OK

GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
  git -c core.excludesFile=/dev/null diff --check
```

The browser-free coverage exercises canonical filtering, installation-state
persistence, rollback on save failure, invalid-command rejection, state
broadcast, and operator-visible persistence failure.

The living manifest/Remote Playwright journey now covers the visible
venue-scope label, separation from manifest state, save + reload, unchanged
patch bytes, the existing fleet/per-seat Remote sections, and unconditional
desktop Device Actions.

## Browser boundary

```sh
~/.venvs/bopos/bin/python tests/verify_manifest_param_visibility.py
```

Chromium exited before loading the app because this managed workspace denies
its macOS Mach rendezvous registration:

```text
bootstrap_check_in org.chromium.Chromium.MachPortRendezvousServer: Permission denied
```

The new Playwright assertions are therefore present but **not claimed passed
in this session**. No iPad/touch, hardware, Pure Data, or audible verification
was performed; none is required by the storage/wire scope of this stitch.
