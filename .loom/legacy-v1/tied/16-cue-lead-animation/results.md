# Cue lead animation — results

The selected Lead value now directly controls the cue button's visual
countdown. A subtle left-to-right fill runs for the complete lead interval,
then the same unchanged cue label flashes brightly for 300 ms at the expected
trigger moment. Duplicate taps remain disabled until the flash completes.

Reduced-motion mode replaces the moving fill with a static scheduling state and
the flash with a brief bright static trigger state.

## Verification

Passed on 2026-07-16:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/ui-tabs/tabs-3-next-sweep/16-cue-lead-animation.stitching/verify_cue_lead_animation.py
# 7/7

node --check dashboard/static/js/facilitator.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  .loom/threads/ui-tabs/tabs-3-next-sweep/16-cue-lead-animation.stitching/verify_cue_lead_animation.py
git diff --check
```

The real Dashboard and touch Chromium test checks both 400 ms and 900 ms Lead
values, the bright trigger transition, unchanged label, reduced-motion states,
and browser errors. Visual evidence is `cue-trigger-flash-ipad.png`.

No `.pd` file changed. Real iPad/Safari, installation Wi-Fi, a real Pi, and
audible cue response were not exercised.
