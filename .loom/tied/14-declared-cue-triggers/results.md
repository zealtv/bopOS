# Declared cue triggers — results

The active fleet patch's declared cues now appear as synchronized live actions
on both the embedded and standalone Dashboard surfaces.

## UX result

A dedicated UX/UI review treated cues as fleet-global actions rather than a
third Seat/Group scope. The resulting compact panel sits above the **All &
Groups / Seats** switch, preserves manifest order, and uses a responsive
three/two/one-column grid. Buttons show `label || id`, optional description,
and a subtle ID only when it differs from the label. The shared Lead field
keeps the existing 100–10000 ms scheduler range.

The live free-text cue field was removed; undeclared cue trials remain in Patch
edit. The whole panel hides when there are no declared cues. The idle
"scheduled against the shared clock" text is gone; the live region reports
only concrete scheduling actions.

## Verification

Passed on 2026-07-16:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/ui-tabs/tabs-3-next-sweep/14-declared-cue-triggers.stitching/verify_declared_cues.py
# 9/9

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/12-dashboard-live-controls/verify_live_controls_backend.py
# 20/20

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/13-diagnostic-density/verify_diagnostic_density.py
# 17/17

node --check dashboard/static/js/dashboard.js
node --check dashboard/static/js/facilitator.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/server.py \
  .loom/threads/ui-tabs/tabs-3-next-sweep/14-declared-cue-triggers.stitching/verify_declared_cues.py
git diff --check
```

The focused test launches the real Dashboard, captures the emitted OSC
datagram, and drives touch-sized Chromium. It verifies manifest order,
label/description/ID hierarchy, exact `/cue snap <shared-time>` delivery,
lead-time feedback, transient textual state, 44 px targets, one embedded copy,
zero-cue hiding, and no browser errors. Visual evidence is
`declared-cues-ipad.png`.

No `.pd` file changed. Real iPad/Safari, installation Wi-Fi, a real Pi, and
audible cue response were not exercised.
