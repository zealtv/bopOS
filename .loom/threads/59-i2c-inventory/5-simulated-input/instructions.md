# 5-simulated-input

**Status:** blocked on `0a-io-design-review` · wanted, not urgent
**Goal:** simulated sensor input from the dashboard, so patches can be developed
and chains debugged without hardware.

Bob, 2026-08-05, after hearing the CLI version work: *"we want to keep that and
will want to build that into the dash in a user friendly way at some point."*

## What exists

`tools/iosim.py`, verified audible on Bob's laptop (`[r bopos-io]` →
`[route adc]` → `[bop.casio~]`). It sends OSC bundles to `127.0.0.1:6662` like
the real bridge. Modes: **stream + press**, **interactive** (stdin), **listen**.

Two fidelity rules, both learned the hard way:

1. **Stream continuously at poll rate**, not only during a press — otherwise the
   patch's `[change]` swallows the first press.
2. **Press goes to the opposite rail from that channel's rest.** Polarity is per
   channel (A1 rests low; A0/A2 rest high).

## The open question (absorbed by `0a`)

Where does simulation run?

- **Relay** (dashboard → `bopos.py` → engine on a real node): good for debugging
  a deployed device; useless for laptop patching.
- **Local** (laptop dev loop): what Bob actually needed. If only one gets built,
  build this.

Different features sharing a payload — don't merge by accident.

## Notes

- Mirror of `4`: that asks "is the sensor producing values?", this asks "does the
  patch respond?".
- Injecting fake data into a node in a live show is an audio hazard; decide what
  a Device-row control means before adding one.
- `bash/start-laptop.sh` doesn't exist (old docs referenced it). If a laptop dev
  loop is built, that's where it goes.
