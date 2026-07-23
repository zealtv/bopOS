# 2-audio-config-implementation

Build the ratified device-audio-config design from `1-audio-config-design`.
Begins `.waiting` on ratification.

## Scope (refine from the ratified design)

- Node side: read/report current audio config + available cards; apply pushed
  config where JACK/the card is configured; persist it; restart the engine as
  the design dictates. Respect the runtime-vs-privileged boundary.
- Dashboard side: the Device-tab controls, current/desired feedback, restart
  affordance.
- Contract amendment + `tools/simfleet.py` parity in the same stitch.

## Verify

- Playwright Device-tab guard driving server + simfleet on non-default ports.
- Real-hardware apply is a Bob/rig gate — say so in the stitch rather than
  claiming the audio actually reconfigured.
