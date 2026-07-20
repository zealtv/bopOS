# Audible Simulation gate — waiting evidence

## Current status after repairs

Bob reran the real macOS/CoreAudio workflow after
`aa-2a-scalar-engine-frames` and reported that audio now works. During that
successful run, the looping/retriggering `go` step exposed a second issue: the
audible LFO retained its shared phase while its Dashboard animation restarted
out of phase at the retrigger.

Tied child `aa-2b-lfo-retrigger-phase` repaired that mismatch by carrying a
leader-monotonic phase sample in runtime Dashboard automation state. Its
focused retrigger proof passed 4/4 and the adjacent facilitator animation suite
passed all 13 checks. The sole remaining gate is one in-person replay of `go`
to confirm the audible and visual LFOs now remain aligned across a retrigger.

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
The initial full-scale-headroom hypothesis was superseded by the follow-up
below.

## Root cause established from the follow-up

Bob isolated Seat 0 and observed:

- ordinary sliders behaved normally before starting the step;
- starting `go` caused immediate distortion;
- distortion remained after stopping automation;
- `gain0 = 0` and `gain1 = 0` did not silence it;
- reducing master to about 0.3 or below made the audio begin to clear.
- the persistent audio was recognizably the synths feeding element 0 and
  element 1, not the separate cue or point noise paths.

The first float fade engine frame is `/p/gain0 1 5000`; LFO frames are
`/p/gain1 <value> 30`. In `demo-pd`, each routed message feeds `[clip 0 1]`
before a hardcoded 10 ms `[line~]` message. Pd's documented list behavior
distributes a multi-atom list across an object's main and secondary inlets
when it has no list method. The duration therefore updates a `[clip]` bound;
the fade's `5000` creates the massive persistent gain state. A later scalar
zero is processed through the corrupted clip bounds, while downstream master
still attenuates the result. The left-channel location matches `gain0`'s
element-0 branch.

Bob clarified the intended boundary: bopOS owns ramp evaluation and Pd should
continue receiving scalars. The two-atom emission was therefore a node-side
decomposition bug, despite having been written into the initial §3.2 text and
tests. Child `aa-2a-scalar-engine-frames` corrects shared `paramgen.py` so
production bopos, simfleet, and audition all evaluate float generators at the
existing control tick and send only one-atom numeric engine frames. No `.pd`
file was edited or needs changing for this repair.

## Earlier post-engine-fix diagnostic procedure

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
take-over, and generator-thread cleanup. Clean audio is now human-confirmed;
this parent remains blocked only on the post-fix retrigger alignment check.
