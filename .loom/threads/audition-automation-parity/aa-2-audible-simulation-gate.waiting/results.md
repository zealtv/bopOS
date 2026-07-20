# Audible Simulation gate — waiting evidence

## Environment and first run

- Date: 2026-07-20
- Host: `Bobs-MacBook-Air.local`, macOS 14.6 (`Darwin 23.6.0`, arm64)
- Engine: Pd 0.55.2, `-nogui -pa` / CoreAudio
- Patch: `patches/demo-pd`
- Show: `dashboard/shows/test.json`, step `go`
- Topology: current Dashboard launched one managed `tools/audition.py` virtual
  Seat and one normal Pd engine. The Dashboard reported that virtual Seat
  online with `engine_alive = 1`.

Bob's audible observation during the saved `go` step:

> significant distortion and crackle

Follow-up characterization:

> sounded like it might a heavily clipped audio channel. it was coming out
> the left speaker. likely the automated node

The harness was interrupted immediately. A read-only process check confirmed
that no `dashboard/server.py`, `tools/audition.py`, or owned Pd process remained.

This is **not** an accepted audible result. The saved step sends `gain0` from
0 to 1 over 5 seconds and runs `gain1` from 0 to 1 as a 4-second triangle LFO.
The left-only symptom is consistent with `demo-pd` element 0 / `gain0`, and
full-scale patch gain may be clipping. That is a hypothesis to distinguish in
the next interactive test, not a concluded root cause.

## Manual comparison for Bob

Use the normal Dashboard and `demo-pd`, with one simulated Seat and master at a
comfortable level. Do not start with the saved full-scale step.

1. Start Simulation and confirm the patch is clean with both `gain0` and
   `gain1` held at `0.10` using ordinary Dashboard sliders.
2. Move only `gain0` slowly through `0.10`, `0.20`, `0.40`, and `1.00`.
   Note the first value at which the left channel clips or crackles.
3. Return `gain0` to `0.10`. Send a conservative fade on Seat 0:
   `/0/p/gain0 0.10 0.20 5s`.
4. Hold `gain0` at `0.10`. Send a conservative LFO:
   `/0/p/gain1 lfo tri 0.05 0.15 4s`.
5. If both conservative generators sound clean, repeat one at a time with a
   higher maximum to find whether the symptom follows amplitude rather than
   automation.
6. During a clean fade/LFO, confirm the Dashboard marker/thumb agrees by eye.
   Take over with a plain slider value and confirm motion/audio stops at once.
7. Stop Simulation, return to Live fleet, and confirm audio/process cleanup.

Interpretation:

- plain `gain0` clips at the same level as the fade: patch/output headroom,
  not generator parity;
- conservative plain value is clean but conservative fade crackles: investigate
  the Pd ramp delivery or generator emissions;
- fade clean, LFO crackles at conservative levels: investigate the 30 ms LFO
  ramp cadence / Pd receiver path;
- both conservative generators clean: revise the saved `test` show's audition
  levels in a separate authorized edit, then repeat the full gate.

## Automated evidence already complete

The tied child `aa-1-audition-generator-parity` proves the relay/engine UDP
boundary (12/12 focused checks), shared parameter generator semantics (32
checks, zero failures), managed parameter catch-up (6/6), selector isolation,
take-over, and generator-thread cleanup. This parent remains specifically
blocked on an acceptable human-audible result and visual confirmation.
