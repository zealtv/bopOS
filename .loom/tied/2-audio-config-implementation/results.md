# Device audio configuration — implementation results

## Outcome

Physical Devices now report and transactionally apply node-level sound-card and
JACK configuration from the Dashboard's Device tab.

- `python/audio_config.py` owns detected ALSA playback-card/mixer discovery,
  complete five-field validation, atomic `bopos.config` updates, and the
  boot-local active snapshot.
- `bash/start-engine.sh` consumes `JACK_SAMPLE_RATE`, `JACK_PERIOD_SIZE`, and
  `JACK_NPERIODS` alongside the existing card/mixer values and records active
  state only after JACK readiness.
- Exact physical `/all/os/to <uid> audio-config <json>` applies under the
  existing admin serialization lock. Failed candidate startup restores the
  old file and restarts the old engine configuration; failure to recover is
  separately attributable.
- Successful candidate and rollback starts reapply effective Device enabled /
  MUTE ALL safety. A candidate that cannot enforce required silence is rejected
  and rolled back.
- `/os/report` and `/os/audio-config` expose configured, active, detected-card,
  status, and error state under contract v1.11.
- The Device Audio panel offers detected cards only, Auto/enumerated mixer
  controls, bounded JACK selects, approximate buffering, saved-versus-active
  feedback, confirmation, apply timeout/requery, and terminal rollback state.
- Physical routing remains invariant in Live, Simulation, and Patch Edit.
  Simfleet and audition speak the same report/request/receipt shape with a
  synthetic stereo card.

No `.pd` file changed. No provisioning or boot-overlay surface was added.

## Verification

Passed:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  -m unittest discover -s tests -v
# 38/38

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile python/audio_config.py python/bopos.py \
  dashboard/osc_bridge.py dashboard/server.py tools/simfleet.py \
  tools/audition.py tests/test_audio_config.py \
  tests/verify_device_control_modes.py

node --check dashboard/static/js/dashboard.js
bash -n bash/start.sh bash/start-engine.sh bash/stop-engine.sh install-device.sh
git diff --check

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_device_control_modes.py
# 16/16, real Dashboard + Chromium + non-default HTTP/UDP ports
```

The browser journey exercised the complete Audio form and receipt while
Simulation owned execution, proving the command still reached only the exact
physical receiver. It also retained the adjacent Device enabled, MUTE ALL,
Patch Edit, Live restoration, and host-only alias route checks. A captured
1280px Audio panel was visually inspected: all five controls, active summary,
buffer estimate, apply state, and feedback were legible with no page errors.

## Hardware boundary

Not claimed in this software stitch:

- real Pi `aplay` / `amixer` enumeration;
- JACK accepting and audibly switching a real card/rate/buffer/period tuple;
- candidate failure followed by successful real-JACK rollback;
- disabled/MUTE ALL audible silence across a real card change;
- narrow iPad/touch use.

Run those gates on a bench Pi before treating fleet hardware adoption as
complete. The software and browser simulations do not pretend to prove audio.
