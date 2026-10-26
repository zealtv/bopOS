READY FOR REVIEW

Implementation commits: `7daed42`, `2cb59f3`, `555c013`, `9df25da`.
Merged current main in `590bac7` before the final verification, including the
landed event-fields editor. No merge conflicts. The manager owns landing and
loom lifecycle; no lifecycle commands were used.

## Changes by file

- `dashboard/osc_input.py`: pure `translate` returns a translation or rejection;
  declared-only event/parameter lookup, target/group resolution, ambiguity,
  default filling, numeric coercion/clamping and event stamps. Reuses
  `manifest.declared_event`, `coerce_event_field` and the dashboard's manifest
  loader. Thin UDP protocol supports individual messages and bundles. Runtime
  executes through `OSCBridge.send`, records parameter values/automation, owns
  the 50-entry rejection/clamp ring, and implements the injected-clock/scheduler
  `MasterRamp`.
- `dashboard/server.py`: starts/stops the input, exposes `--input-port` (5552
  by default, 0 supported for ephemeral tests), adds `osc_input: {port, recent}`
  to existing public state, cancels fades on project switches, and closes the
  bridge if the input bind fails. No new websocket snapshot type or tab.
- `dashboard/ws_handlers.py`: the existing UI master handler shares the input's
  master setter, so a UI change cancels an outside fade.
- `dashboard/state.py`: durable master uses the fade destination while the live
  master follows ramp steps. Other saves during a fade cannot persist a step.
- `dashboard/osc_bridge.py`: outside-point guard covers motion and catch-up
  frames for two seconds. Motion retains its previous evaluation during the
  guard, so an authored path ending during suppression still emits its final
  frame after the guard expires.
- `python/osc_contract.py`, `docs/OSC-CONTRACT.md`: **v1.23**, with §4.3, the
  5552 port row and §15 entry. Typed fields retain their v1.22 history; the new
  input changes no device-wire grammar.
- `docs/PORTS.md`, `docs/OSC-REFERENCE.md`: nine-port map and sender guide centered
  on the input, typed examples without timestamps, command/range/ambiguity and
  diagnostic rules. Exact-device enabled administration remains documented on
  6660; the full administration grammar remains in the contract.
- `.glean/findings/external-osc-timing.md`: shipped 5552 guidance; regenerated
  the index with `glean.sh index` (its bytes did not change).
- `tests/test_osc_input.py`: 12 tests covering translation, all target forms,
  defaults, timestamps/zero lead, clamping, numeric tags, rejection/ambiguity,
  commands, diagnostics, datagrams, editor manifest/selector behavior, real
  bridge parameter mirrors/automation, point guarding and deterministic ramp
  steps/cancellation/persistence across a restart.
- `tests/verify_global_controls_monitor.py`: uses ephemeral input/stream ports
  to avoid collisions with concurrent worker tests.
- This stitch's `verify_live.py`: repeatable outside UDP -> real dashboard ->
  **two simfleet nodes**. Temporary state/manifest, private ephemeral ports,
  stamped deadline, clamp and optional default, and subprocess cleanup.

## Decisions and review focus

- Incoming event fields clamp before the shared coercion helper; the existing
  helper and other callers retain rejection semantics. Missing required fields
  reject even when their declaration has a default; only optional fields fill.
- Short-form plane ambiguity and reserved-prefix rules follow the proposal.
  Numeric seats normalize to canonical nonnegative int32 selectors. Group
  selectors/names require an existing group. Selectors retain their meaning in
  Patch Edit: its mirror updates only when the forwarded selector matches the
  editor's selector 0; no real Seat mirror is changed in edit mode.
- Parameter arguments pass through unchanged. Scalar mirrors use the existing
  canonicalizer; generators use existing bridge tracking and fade-destination
  persistence. Unsupported scalar values are forwarded without poisoning the
  JSON mirrors. Points also pass through unchanged.
- Sender bundle timetags are ignored: the dashboard stamps events at receipt.
  Out-of-range `/bop/*` commands reject; clamping applies to event fields.
- Master fades flush their destination before step one; immediate UI/OSC
  changes keep the existing save debounce. `master_destination` is runtime
  state read by the durable serializer, not a new project schema field.
- Review master persistence/cancellation and parameter bookkeeping hardest.
  The ring is runtime-only and exposed through the existing `state` snapshot;
  stitch 9 owns its UI. No editor/fire-control JS was changed by this worker.

## Verification

All Python checks used `~/.venvs/bopos`. UDP/boot-process/browser runs needed
escalation outside the sandbox; sandbox failures were not counted as passes.

- Final fast suite (required pre-commit hook, after main merge and final selector
  adjustment); full output in `fast.log`:

```text
Ran 640 tests in 40.440s

OK
```

- `./tools/run-tests.sh browser`, after main merge: **39/39 PASS**. Full output
  in `browser.log`; summary tail:

```text
PASS verify_spatial_cancel.py
PASS verify_state_load_safety.py
PASS verify_target_picker.py
PASS verify_value_box_component.py
PASS verify_wifi_networks.py
PASS verify_ws_snapshot_replay.py
```

- Final focused Globals journey after the last runtime adjustment:
  `globals-browser.log` ends `all global-control checks passed`; no page errors.
- Final two-node input/simfleet check: `live.log` records both nodes firing with
  the same nonzero deadline, `elements=folder/file 1 1`, and no LATE suffix:

```text
PASS: outside UDP -> dashboard stamp, clamp and default -> simfleet on two nodes; isolated ephemeral ports
```

- `git diff --check`: clean. Report commit also runs the fast hook.

No `.pd` file was edited, no real hardware or audio was exercised, and no patch
push or real-LAN claim is made. The qtable/Finn Jet/Ciro Toast hardware check
remains the manager's separate stitch 10. Test subprocesses clean up on exit.


## Manager review 1 addressed

- `dashboard/osc_input.py`: all input-triggered full `state` broadcasts now
  share a 100 ms throttle. The first change publishes immediately; changes
  during the window schedule one trailing flush that publishes the latest
  state, including the final change if the stream stops. Rejections, clamps,
  parameters, lead and mute share this limit. Device sends and lightweight
  master/mute messages stay unthrottled; save debounce is unchanged.
- The throttle accepts an injected monotonic clock and scheduler, and shutdown
  cancels its pending flush.
- `tests/test_osc_input.py`: the deterministic burst regression covers 60
  rejections and 60 parameter writes separately. Each produces one immediate
  state publication plus one trailing publication at 100 ms, with the final
  address/value visible. Continued bursts share the next pending flush, all
  60 parameter messages reach device sending immediately, and shutdown cancels
  the pending callback. Existing synchronous tests inject a scheduler.
- `git merge main`: already up to date before final verification.
- `~/.venvs/bopos/bin/python tests/test_osc_input.py`: 12 tests, OK.
- `./tools/run-tests.sh fast`, outside the sandbox: full output retained in
  `review-1-fast.log`; result:

```text
Ran 641 tests in 39.448s

OK
```

- `git diff --check`: clean. No UI changes; the full browser tier was not rerun,
  as requested by the review. The review-fix commit also runs the fast hook.
