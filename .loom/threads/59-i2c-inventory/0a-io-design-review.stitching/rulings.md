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

## Still to decide

- Who writes to a shared module (two instances, or the operator panel while
  a patch runs).
- The error vocabulary details, and the name for bridge-wide errors.
- Out of scope.
- Revised sequencing for `59/1`–`6`, plus a new stitch for Performance mode.
