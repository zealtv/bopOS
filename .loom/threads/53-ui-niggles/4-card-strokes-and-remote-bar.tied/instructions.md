# 4-card-strokes-and-remote-bar

Follow-up corrections from Bob's review of the target-card implementation:

> i am not seeing the identity strokes. i would like cards to have a maximum
> width of 480px. i would like the master and mute button to be a sticky bar on
> the remote. i want silence all to read "mute" and i would like it inline with
> the master where width permits.

## Scope

- Give every group card the deterministic colour/pattern identity shown for
  that group in the Seats target picker. Do not make the border depend on the
  group being one of the four groups currently visible on the Seats map.
- Keep the white All-target stroke on both Control and Remote.
- Cap target-card tracks at 480px on both surfaces and distribute leftover
  horizontal space between tracks.
- Make Remote's master and mute controls an always-visible bottom bar. They
  share a row where space permits and stack at narrow phone widths.
- Label the normal action `MUTE` and the active inverse `UNMUTE`.

## Verify

- Add browser-free guards for deterministic group identity, the 480px grid
  ceiling, and the Remote live-bar structure/labels.
- Extend the focused Control/Remote browser journey to measure the real card
  borders, track ceiling, and live bar if the managed browser can launch.
- Run `./tools/run-tests.sh fast` before tying and record any browser sandbox
  boundary honestly.
