# Ratified — per-device live-control placement & shape (Bob, 2026-07-25)

Bob ratified `proposal.md`, settled all three open questions, and added a
layout ruling the proposal had not asked about. Authority for implementation
stitches `7-control-surface-component` and `9-device-control-panel`.

## Ratified design

One reusable **`ControlSurface`** component (the param-tree renderer + the
value/gen row from stitch 3) hosted in three places that differ only by **scope**
and **patch**: patch editor, Device tab (this device), Control tab
(All / Group / Seat).

### 1. Collapsed by default

**Bob:** "collapsed by default is fine." Collapse state is remembered per the
existing panel-persistence pattern.

### 2. Offline devices — disabled, showing last values

**Bob:** "disabled, show last values."

The panel is **never hidden** for an offline device. It renders the last known
values, visibly disabled (no writes attempted). This matches the durable
offline/unbound value behaviour already ratified in stage 7 — reuse it rather
than adding an offline branch.

### 3. One code path — scope is the only seam

**Bob:** "yes — same component, different send."

Confirmed: Device-write and All/Group/Seat fanout are the **same** component and
the same render; only the send target differs, parameterised by `scope`. Two
parallel renderers would be a defect, not an option.

### 4. Device-tab ordering (new ruling, not in the proposal)

**Bob:** "move the device actions up directly below the diagnostics while you a
here, device control sits below actions."

Device tab vertical order becomes:

1. Patch diagnostics
2. **Device actions** (moved up — currently below other panels)
3. **Device control** (the collapsed `ControlSurface`)

This is a small independent improvement Bob asked for while the area is open; it
belongs to stitch `9-device-control-panel`.

### Effective patch

The panel renders the device's **effective** patch — the pin if the device is
pinned, otherwise the fleet patch — so the controls always match what the device
is actually running.

### Consequence

This **retires** the Seats-detail vertical-overflow complaint rather than
patching it: per-device controls have a home of their own.
