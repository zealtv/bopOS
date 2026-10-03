# 6-live-sensor-in-patch-edit

**Status:** waits on `0a-io-design-review`
**Goal:** in Patch edit, pick a fleet device and its sensor values stream into
the patch being edited — so Bob patches against a live sensor on a real device.

Bob, 2026-10-03: *"When I go into patch edit mode, if I've got some devices in
the fleet, I'd like to be able to pick a device and have its I2C values get
streamed over to the patch that I'm editing."*

## Shape (for `0a` to confirm)

- The editor's audition engine already takes peripheral input on 6662 —
  that's where `tools/iosim.py` sends. A live device stream should arrive the
  same way, so the patch can't tell live from simulated and needs no changes.
- The device keeps feeding its own engine as normal.
- The stream is a development tool: off by default, one device, ends when
  Patch edit closes or the device is unpicked.

## Done when

- A device picker in Patch edit starts and stops the stream; the UI shows
  which device is feeding the editor.
- simfleet can produce a fake stream, so a browser journey covers start, stop
  and device-offline.
- Hardware: Bob's ADS1115 on Ciro Toast drives a patch open in Patch edit.
  Separate claim; don't make it unless it ran.
