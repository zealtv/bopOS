# PE-4b editor delivery and element target results

## Outcome

Bob's live observation had two parts:

1. The PE-4 static UI was being served immediately from the worktree, but the
   Python dashboard listening on port 8080 had started at 12:39, before the
   PE-4 backend existed. It therefore ignored `set_editor_point` and
   `fire_editor_cue` WebSocket messages. The stale process was stopped and the
   dashboard was restarted in detached tmux session `bopos-dashboard` with the
   same `dashboard/server.py --host 0.0.0.0` launch shape. Local HTTP returned
   200 and the live WebSocket reconnected.
2. The editor point preview now has an element 0 / element 1 target toggle.
   Geometry still travels through the normal `/pt` path. A private loopback
   `/audition/editor-element` control tells the managed edit relay which
   element index to put on the decomposed engine `/pt` message. Switching
   sends zero for every held point on the previous element, then replays held
   values on the new element.

The target defaults to element 0 for each new edit session, survives explicit
restart/relaunch with scratch points, and is never persisted. The edit node's
first heartbeat replays assignment, target, and scratch geometry, closing the
same early-relay UDP race previously seen for parameter catch-up.

No `.pd` file was edited.

## Verification

- `verify_pe4b_element_target.py`: **7/7 passed** against the real dashboard,
  managed no-engine edit relay, headless Chromium, and OSC engine capture:
  element 0 default/delivery; element 0 release; element 1 replay; restart
  retention/replay; declared cue delivery; no browser errors.
- Original `.loom/tied/pe-4-points-and-cues-ui/verify_pe4_points_cues.py`:
  **12/12 passed**.
- `.loom/tied/pe-2-edit-mode/verify_pe2_edit_mode.py`: **27/27 passed**,
  including GUI Pd launch and managed cleanup.
- `.loom/tied/d8-2-simulate-toggle/verify_d8_simulation.py`: **9/9 passed**.
- `.loom/tied/pe-3b-simulator-param-catchup/verify_sim_param_catchup.py`:
  **6/6 passed**.
- `node --check` for both dashboard JavaScript files, Python compilation for
  `dashboard/server.py`, `dashboard/osc_bridge.py`, `tools/audition.py`, and
  the focused verifier, plus `git diff --check`: passed.
- Live restart: PID 21632 (started 12:39) stopped; PID 26000 started in
  `bopos-dashboard`; port 8080 listening; `GET /` returned 200; WebSocket
  accepted.

## Boundary

The real live dashboard was restarted onto the corrected backend, but PE-4b
did not automatically launch Bob's patch or fire its cues after restart. Bob
should reload the already-open browser page so the new element toggle enters
the DOM, then relaunch the desired patch. Audible behavior and the patch's Pd
console remain Bob's confirmation boundary.
