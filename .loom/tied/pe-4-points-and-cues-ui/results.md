# PE-4 points and cues UI results

## Outcome

The patch editor now exposes session-only point scratch controls and immediate
cue firing while edit mode owns the managed audition relay.

- The edit instance is assigned one element at `(0, 0)`, rendered at the
  centre of a stripped spatial map with no listener puck.
- Scratch points support add/select/delete, drag, radius, and falloff. They
  use the normal `/pt` wire and the audition relay's existing node-side
  decomposition, yielding `/pt <pointId> <element> <proximity>` at the edit
  engine.
- Point state lives only in the runtime editor record, never in installation
  points or durable state. Explicit engine restart/relaunch preserves and
  replays it within the same edit session; stopping edit mode clears it.
- Declared manifest cues render as fire buttons. A free-text control can fire
  undeclared IDs. Both use the normal `/cue` scheduler with an immediate
  deadline, so the engine receives the bare `/cue <id>` form.
- No `.pd` file was edited.

## Verification

Commands used `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache` and
`~/.venvs/bopos/bin/python` where applicable.

- `verify_pe4_points_cues.py`: **12/12 passed**. Real dashboard, managed
  no-engine audition relay, headless Chromium, and an OSC engine capture
  socket covered centred origin, absent listener, point creation, separation
  from installation points, radius/falloff, drag decomposition to element 0,
  restart replay, declared and undeclared cues, stop cleanup, durable-state
  exclusion, and browser errors.
- `node --check dashboard/static/js/spatial.js`: passed.
- `node --check dashboard/static/js/dashboard.js`: passed.
- `python -m py_compile dashboard/server.py dashboard/osc_bridge.py
  verify_pe4_points_cues.py`: passed.
- `git diff --check`: passed.
- `.loom/tied/pe-1-contract-v1.4/verify_pe1_cues.py`: **10/10 passed**.
- `.loom/tied/sync-2-helper-cue/verify_sync_helper.py`: all **16 checks
  passed**, including bare engine cue delivery.
- `.loom/tied/pe-3-manifest-editor/verify_pe3_backend.py`: **12/12 passed**.
- `.loom/tied/pe-3-manifest-editor/verify_pe3_manifest_editor.py`: **12/12
  passed**.
- `.loom/tied/pe-3b-simulator-param-catchup/verify_sim_param_catchup.py`:
  **6/6 passed**.
- `.loom/tied/d8-2-simulate-toggle/verify_d8_simulation.py`: **9/9 passed**.
- `.loom/tied/pe-2-edit-mode/verify_pe2_edit_mode.py`: **27/27 passed**,
  including real GUI Pd launch and managed-child/watchdog cleanup.
- `.loom/tied/seam-3-points-node-side/verify_points_node_side.py`: its direct
  real-helper phase passed **6/6** twice. Its later full-stack phase could not
  start simfleet because that retained verifier still passes removed CLI
  option `--meter-interval 0`; current `tools/simfleet.py` rejects the option,
  leaving the verifier with no devices and a `StopIteration`. This is retained
  harness drift, not a PE-4 failure; PE-4's focused test exercises the actual
  dashboard → `/pt` → audition decomposition → engine capture path.

## Boundaries

No real installation node, iPad/touch device, or audible patch behavior was
tested for PE-4. The focused browser test exercises pointer dragging, while
the deliberate hands-on touch/layout audit remains scheduled for tabs-2.
