# Decisions

- Chose Bob's stated fallback: the Show inspector always renders the shared
  control-row face and cyan generator state, but does not animate a runtime
  marker. A Show message is authored data, not a running Seat, so live motion
  would require inventing a clock source that the inspector does not own.
- The row's initial position is an honest authoring-time value where possible:
  a constant's value, an LFO's value at its authored phase, or an explicit
  fade/loop `from`; otherwise it uses the declaration default. This is a
  takeover value, not a claim about live playback.
- Dragging the slider or changing the number box writes one static typed
  argument, replacing `lfo`, `loop`, `fade`, or `stop` exactly as the live
  control row takes over automation.
- Removed the `Value` drawer action because the persistent row now performs
  that job directly. Kept `Stop`: it is a distinct OSC wire form and remains
  a single explicit action in the drawer.
- Text parameters and malformed raw-argument fallback remain on their existing
  paths, as scoped by the stitch.
