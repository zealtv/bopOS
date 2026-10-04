# 5-simulated-input

**Status:** waits on `0a-io-design-review` · wanted, not urgent
**Goal:** simulated sensor input from the dashboard, so patches can be
developed without hardware.

Bob, 2026-08-05, after hearing the CLI version work: *"we want to keep that and
will want to build that into the dash in a user friendly way at some point."*

## What exists

`tools/iosim.py`, verified audible on Bob's laptop (`[r bopos-io]` →
`[route adc]` → `[bop.casio~]`). It sends OSC bundles to the engine's 6662 like
the real bridge. Modes: stream + press, interactive (stdin), listen.

Two fidelity rules, learned the hard way:

1. **Stream continuously at poll rate**, not only during a press — otherwise
   the patch's `[change]` swallows the first press.
2. **A press goes to the opposite rail from that channel's rest.** Polarity is
   per channel.

## Relation to `6`

`6` streams a real device's values into Patch edit; this feeds simulated values
into the same place. Both should arrive the same way so the patch can't tell
them apart — build them as two sources for one input, not two features.

## Notes

- Injecting fake data into a node during a show is an audio hazard. Simulation
  belongs to Patch edit unless Bob says otherwise.
- There's no laptop start script (`bash/start-laptop.sh` was referenced by old
  docs but doesn't exist); Patch edit's audition engine is the laptop dev loop.
