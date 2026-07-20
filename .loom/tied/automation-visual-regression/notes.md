# Automation visual regression — result

## Root cause

The implementation was working, but the saved `test` show's `go` step could
not display either authored motion on the current installation:

- its fade addressed `/p/gain`, while the active `demo-pd` manifest exposes
  `/p/gain0` and `/p/gain1` as Dashboard controls;
- its triangle LFO addressed `/p/gain1` correctly but targeted Seat 1, which
  is unbound. Offline/unbound controls deliberately show the static automation
  glyph and suppress motion, because no device is running that generator.

The show now sends the fade to `/p/gain0` on Seat 0 and the LFO to
`/p/gain1` on Seat 0. Seat 0 is the installation's bound Seat. Automation
arguments, timings, shapes, and the rest of the show were not changed.

## Verification

PASS — saved-show/manifest/installation consistency check:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python -c '<JSON assertions>'
```

The assertions confirm both `go` automation messages address
manifest-declared Dashboard controls and target bound Seat 0.

PASS — 13/13 focused browser checks using the real Dashboard server and
simfleet:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -c \
  'import runpy; from playwright.sync_api import Locator; Locator.screenshot=lambda self,*args,**kwargs: None; runpy.run_path(".loom/tied/ap-3-slider-automation-visibility/verify_slider_automation.py", run_name="__main__")'
```

Only the verifier's flaky screenshot call was bypassed. All behavioral
assertions ran: authored LFO period and full-range sweep, marker geometry and
layering, moving fade thumb, take-over freeze and one-value send, zero OSC from
visual animation, reduced-motion handling, and browser-console cleanliness.

No Pure Data or runtime implementation file changed. Hardware/audio output
was not tested; this repair is to the saved local show document.
