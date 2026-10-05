# Frontend review addendum — 2026-10-05

Seven findings reproduced against main `f623b2cef04d9f1658d37f5ee33121676b7ff2fc`:
one High, four Medium and two Low. The highest priority is a Remote hold timer
that can send reboot after the operator has released the pointer. No runtime
code was changed. This is an addendum to the October 3 review, not a replacement.

Reviewed `control-surface.js`, `control-column.js`, `spatial.js`, `monitor.js`,
`target-picker.js`, `param-generator.js`, `ws.js`, the component and host CSS,
and the new `module-panels.js`/editor-input integration. Read `editor_input.py`,
the relevant server dispatch/projection seams, `device-io.js`, Control/Remote
hosts, and the 59/6 and 59/9 instructions and Monitor transport specification.

## Reproduction and validation

All CONFIRMED findings below use the actual shipped JS in isolated Chromium
fixtures. The fixtures mock installation state and transport, never send a real
device command, and use ephemeral browser storage. Spatial cancellation is a
synthetic PointerEvent case; no physical touchscreen was exercised.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python .loom/threads/74-review-remaining/2-review-frontend-modules.stitching/reproduce_frontend.py
```

The script and `reproduction-results.json` are retained here. It asserts the
current defects, so a repaired implementation should make these assertions fail;
repair children should invert them into living regression checks. Chromium needed
execution outside the filesystem sandbox to launch.

Additional checks all passed:

- `./tools/run-tests.sh fast`: 590 tests, 17.688 seconds, OK.
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/verify_module_panels.py`
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/verify_editor_input.py`
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/verify_control_surface_component.py`

These journeys use temporary dashboard/simfleet data. They establish the tested
software paths, not Pi, chip or audio behavior. The complete browser tier was
not run. No screenshots were requested or written.

## F1. A detached Remote hold button still sends its destructive command

**High · CONFIRMED** — `dashboard/static/js/control-column.js:471`,
`dashboard/static/js/control-column.js:473`,
`dashboard/static/js/control-column.js:403`.

`bindCommandButton` starts a 1,200 ms timer on pointerdown. Cancellation is
attached to that particular button's pointerup/cancel/leave handlers. A normal
card render replaces the button with `innerHTML` without cancelling its timer.
Remote's pointer interaction guard only covers parameter ranges, toggles and
enums (`dashboard/static/js/facilitator.js:108`); command holds do not block the
device-update render. Therefore the release can land on the replacement and
leave the old timer running.

Reproduction key `detached_hold`: real browser mouse down on All's reboot
button, render the column, immediately mouse up, then wait 1,300 ms. The mocked
transport records `{"scope":"all","verb":"reboot"}` despite the short press.
No reboot is sent outside the fixture. The same implementation covers shutdown
and updatebopos. The fixture invokes the render directly rather than waiting
for a live fleet heartbeat.

**Suggested route:** repair child under `67-repair-pass`. Track pending holds
at component lifetime, cancel them before replacement/destruction, and ensure
release/cancel ends the active hold even if its node changed. Do not merely
freeze the UI indefinitely. Cover heartbeat replacement and destruction in the
repair's browser regression.

## F2. Simulated input controls are enabled with null values after reconnect

**Medium · CONFIRMED** — `dashboard/static/js/module-panels.js:417`,
`dashboard/static/js/module-panels.js:207`,
`dashboard/static/js/module-panels.js:39`.

Disconnection clears every panel's `values` to null but leaves `ready` true.
Reconnection's refresh enables an already-ready simulated slider before a fresh
`editor_io` sample has restored the array. An unchanged editor session makes
`syncEditor` return without rebuilding that panel. Moving the slider in that
interval executes `panel.values[index] = value` and throws, rather than sending
the input. A held-pad release also uses `drive` without a null guard.

Reproduction key `reconnect`: create simulated ADC, receive one sample, emit
connection false then true, and drive before another sample. Result:
`enabledBeforeFreshSample: true` and
`TypeError: Cannot set properties of null (setting '0')`.
This proves the callback ordering defect; it does not measure the duration of
the real network race or claim every reconnection encounters it. The server
can also reset the owning editor source on disconnect, so the stale client
state should remain inert until the reconnect snapshot arrives.

**Suggested route:** repair child under `67-repair-pass`. Invalidate readiness
on disconnect and make the drive/release path safe until current session data
is received. Verify both slider and held-pad cases.

## F3. Editor live panels ignore late module discovery and inventory changes

**Medium · CONFIRMED** — `dashboard/static/js/module-panels.js:254`,
`dashboard/static/js/module-panels.js:268`,
`dashboard/static/js/module-panels.js:279`.

`syncEditor` derives live panel names from the selected device's report, but its
change signature contains only editor generation, source and editor manifest
modules. Choosing an online device before its IO report arrives creates no
panels. A later `device_update` calls `syncEditor`, but the unchanged signature
returns before reading the newly available inventory. Panels stay absent until
the source or another signature field changes. The same gate prevents automatic
reconciliation when a selected device's module names/types change.

Reproduction key `late_modules`: choose device `dev` with an empty reported
inventory, add a running ADC to its report, emit device_update. Panel count is
zero before and after. This is a fixture report arrival, not a chip scan.

**Suggested route:** repair child under `67-repair-pass`. Reconcile editor-owned
panels against the selected device's current module identity/type metadata,
preserving unrelated manually opened panels and existing input focus/history
where appropriate. Check first report arrival, removal and type replacement.

## F4. Pointer cancellation leaves Spatial permanently in a drag

**Medium · CONFIRMED** — `dashboard/static/js/spatial.js:353`,
`dashboard/static/js/spatial.js:471`, `dashboard/static/js/spatial.js:57`.
The editor map has the analogous pair at lines 678 and 696.

The maps set drag state and pointer capture on pointerdown, but clear their
drag state only on pointerup. Neither map handles pointercancel or unexpected
lostpointercapture. A cancelled gesture leaves `Spatial.dragging` true and
the normal map's render guard prevents later fleet state from appearing.

Reproduction key `spatial_cancel`: start a seat drag, dispatch pointercancel,
add a second Seat, render. Result: dragging remains true and only one Seat is
drawn. Pointer capture is stubbed for this synthetic event fixture. The seat
path is executed; the equivalent editor/listener/point branches are inferred
from their shared missing cancellation cleanup, not separately reproduced.

**Suggested route:** repair child under `67-repair-pass`. Give both maps an
idempotent gesture cleanup path for up/cancel/lost capture. Keep cancellation
semantics explicit so a cancelled click does not select/toggle a Seat.

## F5. Generator segment removal gates become stale after editing rows

**Medium · CONFIRMED** — `dashboard/static/js/control-surface.js:882`,
`dashboard/static/js/control-surface.js:892`,
`dashboard/static/js/param-generator.js:231`.

`panelSegmentRow` sets Remove's disabled state from the count at creation.
Adding/removing a row only rebinds handlers; it never recomputes that state for
existing rows. Starting from a one-segment fade and adding rows leaves the first
Remove disabled. Starting from a two-segment loop, removing one leaves the last
Remove enabled and a second click deletes the last segment. Compile rejects
the empty generator, so this is a broken authoring affordance rather than a
confirmed malformed command reaching the engine.

Reproduction keys `drawer_rebinding` and `empty_loop`: six fade rows retain a
disabled first Remove; the two loop rows can be removed to zero.

**Suggested route:** repair child under `67-repair-pass`, together with F6.
Recompute removal gates from the current DOM count after each structural edit
and enforce the valid lower bound in the action itself.

## F6. Generator rebinding accumulates listeners on surviving drawer nodes

**Low · CONFIRMED** — `dashboard/static/js/control-surface.js:786`,
`dashboard/static/js/control-surface.js:872`,
`dashboard/static/js/control-surface.js:889`,
`dashboard/static/js/control-surface.js:895`.

Changing kind or adding/removing a segment calls `bindGenerators` on the whole
parent again. Surviving drawers receive fresh anonymous focusin/focusout
listeners each time; their mini-slider input and shape-change listeners are
also added again when the corresponding controls survive. Rebinding all sibling
drawers amplifies the accumulation. A wholesale heartbeat render eventually
discards these nodes, but focused editing intentionally defers that render.

Reproduction key `drawer_rebinding` instruments actual listener registrations:
initial bind plus five Add clicks gives six focusin and six focusout listeners
on the same drawer. No heap-growth estimate or user-visible slowdown is claimed.

**Suggested route:** repair child under `67-repair-pass`, combined with F5.
Bind stable drawers once (delegation or explicit stable handlers), and bind only
new controls after structural changes. Verify edits in one drawer do not rebind
its siblings.

## F7. Removed Control cards retain global target-picker listeners

**Low · CONFIRMED** — `dashboard/static/js/target-picker.js:417`,
`dashboard/static/js/control-column.js:514`.

Every `TargetPicker.create` registers an anonymous window storage listener,
even with followFocusSeat false. The closure retains its host, spec and callbacks.
The returned API offers no destruction hook, and ControlColumn.destroy only
removes the DOM host. Adding/removing Control cards therefore leaves listeners
and their associated component closures reachable until the document closes.
The false-follow-focus listeners do not render, but they still retain state.

Reproduction key `picker_cleanup`: create and remove 20 picker hosts with
followFocusSeat false; 20 window storage listeners remain registered. The
fixture counts registrations, not garbage-collected heap bytes.

**Suggested route:** repair child under `67-repair-pass`. Install the storage
listener only when needed, expose picker cleanup, and invoke it from card
destruction. Verify repeated card creation/removal returns global subscriptions
to their baseline.

## Coverage notes and routes not promoted

- **Escaping:** device/module names and report errors in the inspected templates
  are escaped or assigned through textContent. The module slider limits come
  from the host's driver catalog. No concrete device-string injection found in
  this scope. This is code review, not an exhaustive adversarial/security test.
- **CSS:** the fast suite's component-ownership tests pass. Checked shared
  panel/drawer, picker, card, module and host rules and theme/viewport coverage
  from the existing journeys. A static class-reference census produced apparent
  misses `live-param-enum`, `live-param-text`, `live-param-toggle`, `slot-0`; all
  are generated dynamically, so they are not dead CSS. Transparent inner
  live-card content is nested inside the painted target-card shell. No new
  actionable dead-CSS finding; **route: drop**.
- **Heartbeat work:** Remote and desktop Control still replace whole card
  markup on device updates, and Modules rebuilds the editor source options on
  each update. This remains a *likely* fleet-scale cost, with no fleet-scale
  timings gathered here. F1 demonstrates a correctness consequence of that
  replacement. Keep performance measurement within existing `69/5` frontend
  work before prescribing a caching/refactoring system; **route: 69 structure,
  existing work, no proposed new stitch**.
- **Small stale API:** `control-column.js:513` exports no-op `setSole`; no
  production caller was found. Old iframe-era prose also remains in the control
  surface, picker and CSS headers. These do not justify individual repairs;
  **route: 70 dead-code when that pass next touches these files**.
- **Focus sentinel:** the fixture also records focusedSeat returning 0 for an
  absent localStorage key (`target-picker.js:43`, Number(null)). No active host
  opts into followFocusSeat now; **route: drop as an operator-facing bug**, or
  correct the helper if that feature is retained during cleanup.
- **Websocket broker:** latest snapshot replay, bounded pending events and
  generation filtering are present. No additional confirmed broker defect.
  Existing snapshot/transport tests passed as part of fast. Monitor's console
  and report/error displays use textContent and bounded histories; no second
  visual IO socket or per-heartbeat websocket handler registration was found.

No lore item or loom stitch was created, no stitch was tied, and no commit was
made. Another worker's USB worktree and its artifacts were left alone.
