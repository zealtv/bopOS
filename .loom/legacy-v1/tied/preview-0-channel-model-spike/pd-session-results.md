# PD audition session results — 2026-07-13

Bob built and tested the private `bopos.audition~` matrix interactively. The
agent inspected and guided the work but did not edit any `.pd` file.

## Matrix and safety behavior

- Fixed input/output ABI: two signal inputs and two signal outputs.
- Matrix ordering: `l0 l1 r0 r1`.
- DSP equation: `L = x0*l0 + x1*l1`; `R = x0*r0 + x1*r1`.
- Four gains use `line~` with 20 ms ramps.
- Load initialization applies identity `1 0 0 1`; reopening does not mute.
- A full Pd close/reopen passed the cold-start gate: before any valid preview
  frame, an invalid two-value frame retained identity pass-through; a later
  valid off-centre frame applied correctly, and identity restored correctly.
- Complete local frames enter through `bopos-audition-matrix`.
- Arity must be exactly four. Non-float, NaN, infinity, negative, and greater
  than one values are rejected. Rejection retains the last valid matrix.
- Rapid alternating frames passed at 40 ms and 10 ms update rates with no
  audible clicks, ticks, bursts, NaNs, or momentary silence.

## Listening results

- All four one-hot routes reached only the intended source/output channel.
- Two independently positioned mono inputs sounded correct at symmetric
  intermediate and centre constant-power gains.
- A one-position stereo input sounded acceptable through centre,
  intermediate-left/right, and collapsed hard-left/right candidates.
- Bob described the provisional intermediate stereo-width law as sounding
  "pretty good" and did not find the hard-extreme collapse objectionable.
- Production `bopos-master` behavior remained correct at 1, 0.5, 0, and back
  to 1 under identity and off-centre audition matrices. Notification behavior
  remained intentionally outside the production master.

## DSP measurements

Bob measured inside `bopos.out~` with steady inputs `x0=0.1`, `x1=0.2`; all
expected values passed (within PD float precision):

| Matrix (`l0 l1 r0 r1`) | Expected L | Expected R |
|---|---:|---:|
| `1 0 0 1` | 0.100000 | 0.200000 |
| `0.92388 0.382683 0.382683 0.92388` | 0.168925 | 0.223044 |
| `0.707107 0.707107 0.707107 0.707107` | 0.212132 | 0.212132 |
| `0.92388 0.382683 0 0.541196` | 0.168925 | 0.108239 |
| `0.707107 0.707107 0 0` | 0.212132 | 0.000000 |

## Explicit limitation

Two instances of `bopos.audition~` in one PD canvas do not isolate their
current internal send/receive buses. Bob elected to leave this as-is because
the Wave 1 production boundary has one private audition helper inside the one
public `bopos.out~`, and the required internal measurement passed. Do not claim
multi-instance abstraction support from this spike. If that becomes a real
requirement, make the internal buses instance-local in a later Bob-owned PD
edit and retest.

## Agent-side completion

The pure controller model and automated fixtures subsequently passed. The
private network frame is frozen as `/audition/matrix <l0> <l1> <r0> <r1>`;
the selector/target remains outside the local engine frame. See `results.md`
and `verify_audition_matrix.py` for the retained contract and evidence.
