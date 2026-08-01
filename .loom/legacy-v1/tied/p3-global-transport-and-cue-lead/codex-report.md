# Codex report — p3 global transport and cue lead

Completed the task. No `.pd` files were touched and no Loom command mutated
state during the work; Loom writes are confined to this stitching directory.

## Change 1 — global transport controls

- Added compact global play/pause, stop, and next glyph buttons to the Show
  transport action cluster, before the playing indicator.
- Play chooses the exclusive active step when pausing/resuming. With no active
  step it starts the focused step, the step containing the focused message, or
  the first document step in that order.
- Stop and next target the active playing-or-paused step and render disabled
  when no active step exists.
- All global actions use `sendTransport`, including the glyph-only Stop-all
  button, so the p1 optimistic UI path covers them.
- Stop-all retains danger styling plus `title`/`aria-label="Stop all steps"`.
- Reused the existing `.show-icon-button` and play/pause/stop/next glyph CSS.
  The transport icons are 30 px with the existing expanded `::after` hit area.
- Reduced transport-strip vertical padding from 18 px to 10 px after the
  compact-row verifier showed the new policy controls added 16 px to the
  768×1024 layout. The final dense-layout check passes exactly within budget.

## Change 2 — forward-sync retirement

- `ShowEngine` now emits every Show `/cue` through `OSCBridge.fire_cue`; the
  forward-sync argument was removed from `_emit_messages` and `_send_message`.
  `fire_cue_now` remains in place for the editor/non-Show surface.
- `show_model.clean_step` ignores and drops legacy `forward_sync` keys. New
  steps and successful Show saves no longer contain the key.
- Removed `forward_sync` from `update_step` model handling and the server's
  accepted update fields.
- Removed the inspector checkbox, mixed-message sync hint, change handler, and
  now-unused hint CSS.
- Appended the dated global cue-policy amendment to
  `.notes/show-tab-design-2026-07-18.md`.

## Change 3 — global cue lead

- Added installation-state `cue_lead_ms`, default 500 and clamped to
  100..10000 by `InstallationState.clean_cue_lead_ms`.
- Copied the existing installation-setting plumbing used by `master`:
  `InstallationState.data` default → load cleaning → `durable()` JSON → venue
  load/rollback coverage. The new `set_cue_lead {ms}` WS handler validates and
  clamps the integer, updates `state.data`, calls the same one-second
  `save_debounced()`, and broadcasts full `state` so all connected clients
  converge.
- `Dashboard` passes `ShowEngine` a callable over
  `self.state.data["cue_lead_ms"]`; `_send_message` invokes it at cue-fire time,
  so changes are live rather than copied at engine construction.
- Added the settled compact `cue lead · ms` input beside the global transport
  buttons. This placement keeps transport policy with transport controls, not
  the diagnostic consoles. It commits on `change`, mirrors state broadcasts,
  and preserves/focuses an in-progress value across renders so a broadcast
  cannot clobber operator typing.
- Facilitator cue firing remains a per-fire override. Its input now follows
  broadcast `cue_lead_ms` until the operator edits that input during the
  current session, after which broadcasts leave the override alone.

## Focused verifier

Added `verify_show_transport.py` using the house real-server + simfleet +
headless-Chromium harness with random loopback ports, marker-based repo lookup,
one type-aware dialog handler, teardown, and failure exit status. It covers:

- first/focused global start, global pause/resume/stop/next, and glyph Stop-all;
- two-client lead agreement;
- a captured simfleet `/cue` `sharedTimeNs` measured against leader
  `monotonic_ns` at 1200 ms with ±400 ms tolerance;
- persistence across a real server restart;
- legacy true/false `forward_sync` load and save normalization;
- browser page errors.

## Permitted tied-suite amendments

- `.loom/tied/3-playback-engine/verify_show_engine.py`: removed obsolete
  `forward_sync` update fields and changed the former immediate-cue expectation
  so both Show cues must use the ~500 ms scheduled path.
- `.loom/tied/5-inspector/verify_show_inspector.py`: replaced checkbox/hint
  interaction and persistence assertions with an assertion that both retired
  elements are absent.
- Tied browser suites regenerated
  `.loom/tied/5b-compact-rows/after-compact.png` and
  `.loom/tied/5c-target-model-and-picker/target-picker.png`; per the task spec,
  these generated screenshots were not restored.

## Verification

Final acceptance results:

```text
~/.venvs/bopos/bin/python .loom/threads/15-show-polish/p3-global-transport-and-cue-lead.stitching/verify_show_transport.py
14 checks passed; 0 failures

~/.venvs/bopos/bin/python .loom/tied/3-playback-engine/verify_show_engine.py
32 checks passed; All checks passed

~/.venvs/bopos/bin/python .loom/tied/p1-zero-value-and-transport-bugs/verify_show_polish_bugs.py
6 checks passed; 0 failures

~/.venvs/bopos/bin/python .loom/tied/p2-exclusive-playback-and-progress/verify_show_exclusive.py
9 checks passed; 0 failures

~/.venvs/bopos/bin/python .loom/tied/4-tab-ui/verify_show_tab.py
8 checks passed; 0 failures

~/.venvs/bopos/bin/python .loom/tied/5-inspector/verify_show_inspector.py
9 checks passed; 0 failures

~/.venvs/bopos/bin/python .loom/tied/5b-compact-rows/verify_show_compact.py
12 checks passed; 0 failures

~/.venvs/bopos/bin/python .loom/tied/5c-target-model-and-picker/verify_show_targets.py
10 checks passed; 0 failures

~/.venvs/bopos/bin/python .loom/tied/6-message-editing/verify_show_editing.py
18 checks passed; 0 failures

~/.venvs/bopos/bin/python .loom/tied/6b-show-management/verify_show_management.py
11 checks passed; 0 failures
```

Additional final audit:

```text
git diff --check
PASS

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/show_engine.py dashboard/show_model.py dashboard/server.py \
  dashboard/state.py dashboard/osc_bridge.py \
  .loom/threads/15-show-polish/p3-global-transport-and-cue-lead.stitching/verify_show_transport.py \
  .loom/tied/3-playback-engine/verify_show_engine.py \
  .loom/tied/5-inspector/verify_show_inspector.py
PASS

node --check dashboard/static/js/show.js
PASS

node --check dashboard/static/js/facilitator.js
PASS
```

During the sweep, the compact verifier initially reported its container at
1040 px; the padding correction above brought it within 1024 px and the rerun
passed. One chained p1 run transiently returned a null Playwright bounding box;
the required standalone command was rerun and all six checks passed.

## Not done / boundaries

- No hardware, iPad/touch, or audible rig verification was performed.
- No commit was made, as requested.
