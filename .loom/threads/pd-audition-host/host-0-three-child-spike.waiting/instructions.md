# host-0-three-child-spike

**Deferred:** this is now the multichannel/DAW strategy. Resume only when the
parent thread's concrete-need conditions are met; default spatial preview is
being built inside `bopos.out~` under `audition-rig`.

Prove the load-bearing `[pd~]` assumptions before designing the launcher or
listener UI. Bob owns the spike patch; agents may provide commands, fixtures,
OSC drivers, capture/measurement scripts, and results, but never edit `.pd`.

## Spike

- Parent starts three `[pd~ -noutsig 2]` children, each opening the unchanged
  `patches/default/main.pd` with a distinct id, run context, and engine port.
- Parent exposes six distinguishable raw signals: child 0 L/R, child 1 L/R,
  child 2 L/R. It alone opens CoreAudio and makes a temporary stereo monitor.
- Run the current audition relay/dashboard against the three child ports.
  Confirm three identities, manifest declarations, master, and selector-specific
  `gain0`/`gain1` control.
- Exercise independent channels using patch controls or a minimal external
  signal fixture; do not modify the default patch merely to make the test easy.
- Record `[pd~]` FIFO setting, block/sample rate, measured or bounded latency,
  CPU for parent + children, startup time, and any console errors.
- Stop through the parent/launcher and prove every subprocess and port exits.

## Acceptance

The spike passes only if all six raw channels are independently observable,
dashboard control remains device-specific, the audible parent mix is stable,
and teardown is ownership-safe. Compare CPU and subjective behavior with tied
N-process Stage 0; this is a proof, not yet the permanent host implementation.

If arbitrary `main.pd` cannot run unchanged under `[pd~]`, record the exact
incompatibility and stop for Bob rather than inventing a cloneable patch API.
