# Verification

Passed on 2026-07-30:

```text
node --check dashboard/static/js/param-generator.js
node --check dashboard/static/js/control-surface.js
node --check dashboard/static/js/show.js
git diff --check

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python tests/verify_generator_drawer.py
Generator drawer checks passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python tests/verify_live_param_kinds.py
Live-param kind browser checks passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python tests/verify_show_generator_drawer.py
12 checks passed, 0 failures

./tools/run-tests.sh fast
Ran 250 tests — OK

./tools/run-tests.sh browser
18/18 browser verifiers passed
```

The focused Show journey uses one fixture message per wire kind. It covers
the shared three-tab face, waveform body, fixed 320px width, disclosure and
field persistence, generator-kind switching, and explicit Value/Stop wire
forms.

No physical device, iPad/touch, Pure Data, audible, or hardware verification
was performed. This stitch changes browser UI and Show authoring only.
