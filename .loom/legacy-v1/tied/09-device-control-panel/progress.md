# 09-device-control-panel — done

The Device tab now drives one device's live controls, through the shared
component, and the panel order Bob asked for while the area was open.

## What shipped

**Device tab order** is now patch diagnostics → **Actions** → **Device
control** → audio → log → assets → report. Actions moved up from below the
assets summary; the control panel is new and sits beneath them.

**The panel** (`deviceControlSection` in `dashboard.js`) renders the shared
`ControlSurface` at `scope: "device"`, collapsed by default with the choice
remembered in `localStorage`. Offline or unbound devices render their last
known values **disabled**, never hidden, with a one-line reason. The panel
names the patch it is showing and says whether that patch is pinned or the
fleet's.

**Server:** `live_control_manifest` / `live_control_declarations` /
`live_param_declaration` take an optional patch name; `live_scope_patch` maps a
scope to the patch that owns its schema; `live_param_target` gained the
`device` scope.

## The schema problem, solved — and where it nearly went wrong

A pinned device runs a *different patch*, so the fleet-wide `live_controls` is
the wrong schema for it. Fixed by publishing the pinned patch's declarations on
the device itself.

First attempt put that in `public_state`, and the verifier caught it: the
roster acts on **`device_update`** broadcasts, which carry one device built by
`public_device` — not the whole state. The schema never reached the client.
Moved into `public_device`, beside the `patch_pinned` axis it belongs to. Only
pinned devices carry their own schema; everything else falls back to the
fleet-wide one, so the extra manifest read is bounded by how many devices are
pinned, not by fleet size.

## Scope on the wire, kept honest

`scope: "device"` carries a uid and resolves node-side to that device's **seat**
selector — OSC v1.5 targets content by seat, and pinning already requires a
seat binding, so there is always one. The code says so in a comment rather than
implying a device selector exists. An unbound device resolves to nothing and
the panel is disabled with the reason shown, which is the same requirement
`11-set-patch-handoff` offers to fix in one click.

## Verification

- **`tests/verify_device_control_panel.py` — new, 12/12 green.** Panel order;
  collapsed by default and remembered across a reload; the rows come from the
  shared component at device scope; a device write reaches the wire and lands
  on **that device's seat only**; a **pinned** device renders its own patch's
  params (`shimmer`) and not the fleet's (`density`); and a device taken
  offline mid-test still shows its panel with every control disabled.
- Regression: `verify_device_patch_targeting` 14/14,
  `verify_control_surface_component` 11/11, `verify_generator_drawer` 38/38,
  `test_device_patch_override` 7/7, `test_device_enabled`,
  `test_device_control_routing` 5/5 — all green.

## Noted for the next reader

The offline sweep marks a device down **30 s** after its last heartbeat, so any
test that kills the fleet and waits for `online === false` needs a timeout
longer than that. Cost a run to learn.

## Seats-detail overflow

The ratification says this panel *retires* the Seats-detail vertical-overflow
complaint rather than patching it. Nothing was removed from the Seats detail in
this stitch — the per-device controls now have a home of their own, which is
the substantive fix; deciding what (if anything) is now redundant in the Seats
inspector is a UX call for Bob, not a silent deletion.
