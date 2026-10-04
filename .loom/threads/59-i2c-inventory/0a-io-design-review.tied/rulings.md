# IO design review: Bob's direction, 2026-10-04 (in session, in chat)

Captured as we talked; `proposal.md` builds on this. Bob chose to talk it
through in the session ("artifact not required").

## 1. Transport

- **`bopos.py` handles it**: the device's only process facing the network.
  Control (scan, create/destroy, registry, errors) uses the existing admin
  path.
- **Streaming data uses a separate, dedicated port** (Bob: *"it should remain on
  a separate port - it will be streaming data"*), device → host, so a stream
  can't crowd control or heartbeat traffic.
- Shape: while a stream lease is open, the bridge copies its bundle to a local
  port `bopos.py` listens on; `bopos.py` checks the lease and forwards to the
  host's stream port. The bridge stays localhost-only.
- The error vocabulary (`67-repair-pass/3-io-bridge-hardening`
  wire-proposal) still needs settling in the proposal.

## 2. Streaming and Performance mode

- The §6 "no streamed telemetry" rule is relaxed for development. Bob: *"strict
  adherence to it has made debugging sensors and development difficult if not
  impossible. it needs to be relaxed."*
- Streaming: one device at a time, opened explicitly, at most the poll rate,
  on a short lease (stops by itself when the tab closes or Patch Edit ends).
- **A global "Performance" toggle** activates Performance mode (Bob's name).
  It's separate from Live / Simulation / Patch Edit, and it's an explicit
  switch in the header, not inferred from show playback.
- **Devices enforce it**, not only the dashboard: the mode reaches every node,
  and `bopos.py` refuses what's locked.
- Performance mode locks:
  - sensor streaming and stream-to-editor;
  - **logging to the SD card**. Bob: the point is *"to protect the sd card in
    the case of a hard shutdown"*, so in Performance logs go to RAM and the
    dashboard only;
  - probes and Monitor sends;
  - **Wi-Fi changes** (Bob added);
  - **patch changes** (Bob added): pushes, Set Live, New Version, manifest
    saves, entering Patch Edit.
- The dashboard starts in development, so Performance is chosen deliberately.

## 3. Ownership

- **Manifest** (Bob: yes). Modules are declared in the manifest (name, type,
  address), fleet-wide, and satisfied per device on the asset-slot pattern
  (each device reports presence; a module can be optional). Engine instances
  hook in by name. Still open: who may write to a module when several
  instances could.

## 4. Workflow

- Agreed: the Device tab is the home for scan, bring-up and status, with
  values in units and exactly as the patch receives them.
- Bob: a checkbox to see and/or interact with a module's ins and outs directly,
  e.g. write to the OLED, or watch ADS, tilt or touch data stream.

## 5. Simulation and module panels

- **One description per module type** (the driver declares its inputs with units
  and ranges, and its outputs/commands). The dashboard draws a generic panel
  from it:
  - live: readouts, plus controls for outputs (OLED text, thresholds);
  - simulated: inputs become sliders and pads sent to the engine through the
    same door a live stream uses, and outputs show what the patch wrote
    (OLED preview).
  - The panel header always names its source (device · live, or simulated).
- **Where:** a "Modules" tab in the Monitor dock, plus a pop-out to its own
  ordinary browser window. Cross-platform; Bob ruled out Chrome-only
  Picture-in-Picture.
- **Simulated values reset each session**, not saved (Bob: *"keep it clean -
  it's for development so state not required"*).

## Settled, second round (2026-10-04)

- **Writes: last write wins.** Bob: *"there aren't ever two engines"*, so no
  per-module writer field is needed. Operator writes from module panels are
  development-only (locked in Performance mode).
- **Errors: adopt the wire-proposal vocabulary.** Documented `create-failed`;
  new `invalid-arguments`, `unknown-command` and `write-failed`; reserved
  name `bridge` for errors not about a module. Errors travel on the control
  path to the dashboard (Device tab and module panel) instead of only the log.
- **Streaming scope: one device at a time, all of its modules** (Bob).
- **Out of scope:** raw register access (drivers only); buses other than I2C
  for now; recording and replaying streams; streaming from more than one device
  at once; cross-device sensor routing (sensor data driving other boxes as part
  of a piece — a composition feature, not this layer).
- **Future (Bob):** server-side decisions from aggregate or specific sensor
  readings, as a separate show-time feed, not the development stream.
- **Panels, settled third round:** interactive module panels live only in the
  Monitor dock's Modules tab. The Device tab is the inventory with a "Show in
  Monitor" checkbox. A live panel lets you watch inputs and drive outputs
  (e.g. set the OLED); a simulated panel drives inputs and shows the patch's
  outputs, editor only. Fake input into a real device's engine is deferred
  (future, if needed). Bob: "sounds good".

## Still to decide

- Revised sequencing for `59/1`–`6`, plus a new stitch for Performance mode.

## Ratified, 2026-10-04

Bob ratified `proposal.md`: ports 5551/7771 fine; Performance mode remembered on each device and never locked (no timeout; Bob saw lockout risk in the fail-safe); Patch Edit locked in Performance including viewing; `4-sensor-test-window` retired into the panels; no "switch to Performance?" prompt, but a **prominent** header toggle.
