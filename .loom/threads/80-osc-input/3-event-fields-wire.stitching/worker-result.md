READY FOR REVIEW

Implementation commit: `ba0b2bb` (Carry typed event fields through the event wire).
Merged local `main` before final verification, without conflicts; its only
incoming change was the sibling worker brief. No loom lifecycle changes.

## Changes by file

- `python/manifest.py`: event `fields` (0–16), shared param kind/value checks,
  unique names, boolean/trailing `optional`, optional defaults, wire-safe
  field defaults/ranges, loud rejection of `arity`/`defaults`. Exposes
  `coerce_event_field(field, value)` for a validated declaration and
  `event_scalar`/`event_values` for manifest-independent wire validation.
- `python/bopos.py`: accepts mixed f/i/s fields within limits, preserves
  scalar types through scheduling, emits their original OSC tags to engines.
- `dashboard/osc_bridge.py`: validates/rounds event values and preserves their
  Python scalar types for OSC tags. `dashboard/server.py`: removes the old
  WebSocket all-float conversion, so typed values can reach that bridge.
- `tools/simfleet.py`, `tools/audition.py`: identical value limits and mixed
  field receipt, scheduling, logging and audition engine delivery.
- `python/osc_contract.py`, `docs/OSC-CONTRACT.md`: v1.22; updated event wire,
  declarations, engine surface and revision history. `docs/OSC-REFERENCE.md`
  includes typed examples and removes the float-only client guidance.
  `docs/RELEASE-NOTES.md` records the required whole-fleet update and patch push.
- `patches/demo-pd/bopos.patch.json`: tracked migration of `snap` to `fields: []`.
  Local ignored `patches/bonks-pd/bopos.patch.json` and
  `patches/kc-test/bopos.patch.json` were migrated in this worktree in place.
- `tests/test_manifest.py`, `tests/test_event_plane.py`: durable field schema,
  coercion, mixed-tag round trip, limits, node rejection, scheduled audition
  and simfleet parity tests. Browser manifest fixtures were migrated in
  `verify_control_surface_component.py`, `verify_control_tab.py`,
  `verify_event_control_panel.py`, `verify_ground_and_card.py` and
  `verify_manifest_param_visibility.py`.
- `verify_live.py` in this stitch: repeatable real-dashboard WebSocket -> UDP
  -> simfleet smoke test, ephemeral ports, temporary state, subprocess cleanup.

## Decisions and review focus

- Field declarations reuse the existing param checks rather than changing
  param requirements. Numeric range/default properties retain those rules;
  optional event fields additionally require a non-null default. Every supplied
  field default/range is checked against the event wire limits.
- `coerce_event_field` expects a validated declaration, including derived
  enum/toggle ranges. It accepts integral numeric input for integer kinds,
  rejects fractions and out-of-range values, and returns the Python scalar
  type the bridge serializes. The future input stitch owns filling omitted
  trailing defaults and rejecting missing required fields; no input was built.
- `kc-test`'s two formerly positional fields are named `element0`/`element1`,
  kind float, default 0, required. No new meaning or range was invented.
- Review the tiny WebSocket validation change: retaining types is necessary
  to keep integers/text intact upstream of the bridge. Zero-field UI firing
  remains supported. No dashboard JS or editor/fire controls were changed.
- Typed field UI and its browser journeys remain stitch `4-event-fields-editor`.
  Numeric-event browser fixtures now use `fields`; their old numeric-box UI
  assertions must be adopted with that stitch. The complete browser tier was
  not run here. The focused Control-tab journey passed.

## Patch distribution and hardware boundary

**Carry the migrated ignored `bonks-pd` and `kc-test` manifest copies from this
worktree when landing. Push all migrated patches with the bopOS update.**
Git pull does not distribute patches. All three local manifests passed
`manifest.load` after migration. Update every node before relying on typed
fields; older nodes silently drop them. No warning UI was added.

No `.pd` file was edited. No hardware, real LAN or audio claim: Bob's
`5-pd-event-fields` must check that `/e/<identity>` delivers symbols mixed with
numbers through `pd/bopos~.pd` unchanged, e.g.
`/e/trig/play "folder/file" 1.0 1`, and make any needed Pd changes himself.
No servers were left running by the live verifier.

## Verification

All Python runs used `~/.venvs/bopos/bin/python` (the test runner selects it).
UDP/integration checks required escalation outside the sandbox; the sandbox
attempt was not treated as verification.

- `~/.venvs/bopos/bin/python tests/test_manifest.py`: 18 tests, OK.
- `~/.venvs/bopos/bin/python tests/test_event_plane.py`: 14 tests, OK.
- `PYTHONPYCACHEPREFIX=/private/tmp/bopos-event-pycache ~/.venvs/bopos/bin/python -m py_compile ...`:
  all changed Python files, migrated browser fixtures and `verify_live.py`, OK.
- `git diff --check`: clean.
- `git merge main`: clean merge before the final runs.
- `./tools/run-tests.sh fast`: final post-merge result excerpt:

```text
Ran 625 tests in 40.129s

OK
```

- `~/.venvs/bopos/bin/python tests/verify_control_tab.py`: 53 PASS checks;
  output tail:

```text
[PASS] Remote has no command strip outside target cards
[PASS] Remote offers no Devices-tab hand-off
[PASS] no standalone page errors

Control tab checks passed
```

- `~/.venvs/bopos/bin/python .loom/threads/80-osc-input/3-event-fields-wire.stitching/verify_live.py`:
  post-merge output tail:

```text
22:11:54 sim1 id=-1 event typed/check fired dev_deadline=0 fire_mono=1960431434604791 elements=folder/file 1.67772e+07 -0.25 1
PASS: real dashboard websocket -> typed UDP -> simfleet receipt; isolated ephemeral ports
```

The final report commit also runs the required fast pre-commit hook.
