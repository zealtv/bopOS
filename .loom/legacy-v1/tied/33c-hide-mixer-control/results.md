# Mixer-control UI ownership correction

Bob removed mixer selection from the operator-facing Device Audio panel.

- The panel now contains sound card, sample rate, buffer size, and periods.
- Same-card edits retain the existing `mixer_control` value when it is still
  reported for that card.
- A card change, or a stale mixer value, sends `mixer_control: null` and leaves
  selection to node-side Auto discovery.
- The v1.11 wire/report field and `bopos.config` support remain unchanged; this
  is a presentation and ownership correction.
- The four-column wide layout retains the existing two-column and single-column
  responsive breakpoints.

Verification:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  -m unittest discover -s tests -v
# 38/38

node --check dashboard/static/js/dashboard.js
git diff --check

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_device_control_modes.py
# 16/16
```

The browser journey explicitly asserted that `#audio-mixer` is absent, that
the remaining settings apply from Simulation to the exact physical receiver,
and that a same-card edit preserves the existing `Digital` mixer value.
