# 5-simulated-input

Bring simulated peripheral input into the dashboard, so a patch can be
developed and a chain bisected without the hardware.

**Direction ratified by Bob, 2026-08-05**, on hearing the CLI version work on
his laptop: *"I can hear that locally. So that's great — we want to keep that
and will want to build that into the dash in a user friendly way at some
point."* The *"at some point"* is real: this is wanted, not urgent, and it
sits behind the rest of this thread.

## What already exists

`tools/iosim.py`, written in the session that raised this thread and verified
audible end-to-end on Bob's laptop through `[r bopos-io]` → `[route adc]` →
`[bop.casio~]`. It works because the bridge's output is not privileged: one
OSC bundle per tick to `127.0.0.1:6662`, which anything can send.

Three modes, all of which the dashboard version will want in some form:

- **stream + press** — hold a rest vector, pulse one channel to the opposite
  rail, release;
- **interactive** — press channels by hand from stdin;
- **listen** — print what a real bridge is sending (only when PD is not
  holding the port).

Two fidelity details are load-bearing and were both found the hard way:

1. **It must stream continuously at the poll rate, not only during a press.**
   The real bridge sends every tick, and the patch's `[change]` holds the last
   value it saw. A simulator that transmits only while pressed makes the first
   press indistinguishable from no change and swallows it. Interactive mode
   runs a pump thread for exactly this reason.
2. **A press goes to the opposite rail from that channel's rest**, because
   rest polarity is per-channel — on the Ciro Toast rig A1 rests at 0 V and
   rises while A0/A2 rest at rail and fall. A simulator with one global
   "press = low" is wrong on a third of the real inputs.

## The question this stitch answers

**Where does the simulation run?** The CLI sends to `127.0.0.1:6662` on the
machine it runs on, which is what makes it useful on a laptop. A dashboard
control is remote, so it must either:

- **relay** — dashboard → `bopos.py` → the engine's peripheral port, injecting
  alongside the real bridge on a real node. Good for bisecting a deployed
  device; useless for laptop patch development, which is the case Bob was
  actually stuck in.
- **stay local** — the dashboard hands the operator a prepared command, or the
  laptop dev loop grows its own surface. Honest, unglamorous, and it keeps
  working when there is no fleet at all.

These are different features that happen to share a payload. Do not merge them
by accident. The laptop case is the one that was blocking; if only one gets
built, build that.

## Notes for whoever picks this up

- `4-sensor-test-window` is the mirror image: it asks *"is the sensor
  producing values"*, this asks *"does the patch respond to values"*. Neither
  substitutes for the other, and a chain with both instrumented is bisectable
  in one step.
- Do not attach this to a Device row without deciding what it means. Injecting
  fake sensor data into a node that is in a show is a live-audio hazard; the
  CLI is safe by being obviously manual and local.
- `bash/start-laptop.sh` is referenced in `CLAUDE.md` under "Testing without
  hardware" but **does not exist in the repo**. If a laptop dev loop is being
  built out here, that is where it belongs, and the stale reference should go
  either way.
