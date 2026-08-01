# Cue label density — results

Bob's hands-on revision is applied: each declared cue button shows only its
`label || id`. Manifest descriptions, secondary IDs, and the visible
panel-level scheduling sentence are absent.

Scheduling leaves the cue name in place and acknowledges the tap visually. The
button remains guarded against duplicate taps through the selected lead window.
`prefers-reduced-motion` uses a restrained static state, while a visually hidden
polite live region retains concrete scheduling feedback for screen readers.
The requested Lead-duration countdown and trigger flash are verified separately
in the immediate `16-cue-lead-animation` follow-up.

## Verification

Passed on 2026-07-16:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/ui-tabs/tabs-3-next-sweep/15-cue-label-density.stitching/verify_cue_label_density.py
# 6/6

node --check dashboard/static/js/facilitator.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  .loom/threads/ui-tabs/tabs-3-next-sweep/15-cue-label-density.stitching/verify_cue_label_density.py
git diff --check
```

The focused test launches the real Dashboard and touch-sized Chromium. Visual
evidence is `cue-label-density-ipad.png`. No `.pd` file changed. Real
iPad/Safari, installation Wi-Fi, a real Pi, and audible cue response were not
exercised.
