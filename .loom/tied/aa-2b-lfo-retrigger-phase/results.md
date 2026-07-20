# Non-free LFO retrigger phase — results

## Cause and repair

The node/audition generator evaluates non-free LFOs against the Dashboard
leader's monotonic clock. The Dashboard visualization instead derived elapsed
time from each automation entry's wall-clock `sent_at`, so an identical message
from a looping/retriggering Show step restarted only the visual oscillator.

`OSCBridge.set_param` now records `phase_at_send_ms` for non-free LFOs, sampled
from the same leader monotonic clock and including the authored phase option.
`ParamSpec.phaseAnchor` uses that sample, while retaining the old fallback for
state without the field and the existing independent visualization for free
LFOs. No OSC frame or Pure Data patch changed.

## Verification

Passed:

- `verify_lfo_retrigger_phase.py`: 4/4. Deterministic bridge samples for two
  identical sends five seconds apart resolve in browser code to the same phase
  at a common instant; free-LFO behavior remains independent.
- `node --check dashboard/static/js/paramspec.js`.
- `python -m py_compile dashboard/osc_bridge.py` with the repository venv and
  `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache`.
- tied `ap-3-slider-automation-visibility/verify_slider_automation.py`: all 13
  facilitator browser checks, including authored LFO period and marker motion.
- tied `pe-3b-simulator-param-catchup/verify_sim_param_catchup.py`: 6/6.
- tied `automation-1-engine-and-parity/verify_param_automation.py`: zero
  failures.

The adjacent tied `01-simulation-transition-coherence` verifier was run twice.
Both times its two backend transition/restoration checks passed, then its old
browser check timed out waiting for `#dashboard-live-view #cards .card`. The
focused facilitator browser suite above passed; this timeout occurs on a Live
iframe surface untouched by this change and is recorded rather than hidden.

## Remaining human gate

Bob confirmed the scalar-engine-frame repair restored clean audio before this
child. The parent audible gate still needs one brief in-person replay of the
looping `go` step to confirm the audible and visible LFOs remain aligned across
the retrigger.
