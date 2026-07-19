# Parameter automation: generator slots, timed fades, and LFOs — design proposal

Status: **draft awaiting Bob's ratification.** Direction was agreed in
conversation 2026-07-19 (see `braindump-2026-07-19.md` for the source and
Bob's rulings); the exact grammar below has not been ratified and implies a
contract revision (§3 shorthand registry and, when the deferred atom slice
lands, §8).

## 1. The model: one generator slot per parameter

Every numeric `/p/*` parameter address has exactly one **generator slot**.
Everything a message can do is "replace the generator":

- A plain value is the degenerate generator: a **constant**.
- A fade (single- or multi-segment) is a **finite generator** that ends in a
  constant at its final destination.
- An LFO is an **infinite generator**.
- `loop` is a finite segment list replayed forever (snap back to the first
  segment's start — it literally loops the curve as written; the triangle LFO
  covers the ping-pong case).
- `stop` replaces the generator with a constant at the current output value.

**Last message wins.** Any message on the address replaces the current
generator, whatever it is. There is no layering and no modulation routing —
a fade over an LFO kills the LFO, a plain value kills anything. This single
rule is also the dashboard take-over gesture (§6).

## 2. Wire grammar (numeric params only)

Extends bop's existing arity shorthand; bare numeric durations stay ms for
back-compatibility.

```
/param x                       set (constant)
/param x <dur>                 go to x in dur, from current
/param x y <dur>               go from x to y in dur
/param a <dur> b <dur> ...     segment list: to a in dur, then b in dur, ...
                               (starts from current; even count; odd ≥5 = error)
/param loop <fade-form>        replay the segment list forever, snapping back
                               to its start (ignored for 1–2 element forms)
/param stop                    freeze at current output
```

Note the 3-element form is the only one with an explicit start value; segment
lists always start from current. Documented asymmetry, kept from bop.

### Durations

A duration is either a bare number (**ms**, legacy) or a string with a unit
suffix: `250ms`, `10s`, `1.5m`, `2h`. **Musical units (beats/bars) never
reach the wire** — they are authoring-layer vocabulary that the dashboard
compiles to ms at send time. This keeps tempo/transport out of the device
contract entirely; it is deferred with the `scene-sequencing` musical-time
co-design. (Bob's `1b`/`b1` positional beats/bars notation is dropped for
being typo-hostile; the authoring layer can spell `beats`/`bars` in the UI.)

### Curve

One optional trailing token, SuperCollider-Env style signed exponent:

```
curve:<n>      n = 0 linear (default when omitted)
               n > 0 ease-in-ish, n < 0 ease-out-ish
```

Ratified over the earlier `1e`/`e1` sketch, whose tokens are lexically valid
float exponent literals and would be silently coerced somewhere in the chain.
One `curve:` token applies to every segment in the message; per-segment
curves are deferred (the GUI may motivate them later — additive).

### Ints

Same grammar. The generator interpolates continuously, output is rounded to
nearest, and each integer value is emitted exactly once per crossing (a patch
triggering per step must be able to rely on no duplicates and no skips at
control rate).

## 3. LFO grammar

```
/param lfo <shape> <min> <max> <period> [phase:<0..1>] [free] [curve:<n>]

/param lfo sine 0.2 0.8 2s
/param lfo saw 0 1 4s phase:0.25
/param lfo sh 100 8000 500ms free
```

Shapes: `sine tri saw square sh drift` (`sh` = sample-and-hold random,
`drift` = smoothed random). `square` may grow `duty:<0..1>` later (additive).
Period takes the same duration forms as fades. `curve:` shapes the segment
interpolation where meaningful (tri/saw/drift).

**Phase is clock-anchored by default**: computed from the sync plane's shared
clock as `((t_synced / period) + phase) mod 1`. This makes an LFO message
**full-state and idempotent** — resending is always safe, the catch-up push
can replay it verbatim, and a late joiner lands in phase with the fleet.
`free` opts out: per-device random phase for deliberate decorrelation.

## 4. Control-plane law and catch-up

The contract's spine — every fleet command full-state and idempotent — is
preserved as follows:

- **LFOs (sync)**: idempotent by construction (clock-anchored phase). Catch-up
  replays the message.
- **LFOs (free)**: resend restarts at a new random phase; declared acceptable
  since decorrelation is the point of `free`.
- **Fades**: not replay-safe mid-flight. The catch-up source sends the
  **computed current value** (a constant) instead of the fade message; a
  rejoining device lands where the fleet is and holds. Once a fade completes,
  its final destination is the stored full-state value.

## 5. Decomposition lives in bopos.py

bopos.py owns the grammar end to end: parsing, units, curves, segment
scheduling, LFO phase math, and the "current value" answer that catch-up
needs. PD engines receive only the primitive they already handle — selector-
stripped `go to x in y ms` segments at segment boundaries, and short
control-rate smoothing segments for LFOs (PD's `line~`-style interpolation
between updates). Consequences:

- 64-bit absolute time never enters PD (house rule holds).
- Existing patches need **zero changes**.
- The entire feature is Python — agent-workable.
- This is the `/pt` precedent (node-side decomposition at every scale), not
  the reverted dashboard-computed `/p/gain` streams: the sender addresses the
  patch parameter directly and the node interprets the message it was sent;
  no framework product is composed into a patch param.

Trade-off accepted: LFO smoothness is control-rate from Python with PD
smoothing, not sample-accurate. Audio-rate modulation is a patch-internal
oscillator, not wire automation.

## 6. Dashboard and Show tab

- **Builder GUI** (Show inspector): constructs fades/LFOs without memorising
  the syntax; it is a compiler to this grammar, and doubles as the grammar's
  completeness test.
- **Animated controls**: the dashboard sent the generator and shares the
  synced clock, so it simulates the animation locally — zero extra OSC
  traffic, deterministic for sync LFOs.
- **Take-over**: touching an automated control sends a plain value; the
  generator is replaced by a constant (§1's last-message-wins).
- **Waveform visualisation**: a small waveform rendering on automated
  controls, doubling as the "this parameter is automated" indicator, quickly
  fading out when touched (the animation dying under your finger is the
  feedback that it is now static). **Needs a UX-designer pass** for an
  app-wide treatment before implementation.

## 7. Strings and mixed arrays are not parameters (deferred slice)

Bob's ruling: rather than making the arity grammar type-dependent (which
would make the wire unreadable without the manifest), string and mixed-array
addresses become a **different manifest kind** — working name **atom**:
declared, typed, set-only, full-state, same `/p/*` plane and selector
routing, but the grammar keywords never apply. If the manifest says atom,
every element is payload; if it says param, the grammar applies. Additive §8
amendment, deferred to its own slice — nothing in the fade/LFO design
depends on it.

## 8. Contract impact

- §3 shorthand-registry revision: the automation grammar (durations, curve
  token, `loop`, `stop`, `lfo`) becomes framework-owned vocabulary on the
  `/p/*` plane; output semantics remain patch-owned.
- Catch-up rule note (§4.1 area): fades catch up as computed constants; sync
  LFOs catch up verbatim.
- Deferred: atom manifest kind (§8, additive); musical time (authoring layer,
  with `scene-sequencing`); per-segment curves; `duty:`; audio-rate anything.

## 9. Open questions for ratification

1. Rounding rule for ints — round-to-nearest proposed; confirm.
2. `loop` + `curve:` + `lfo` keyword ordering/positions — proposal: keywords
   lead (`loop`, `lfo`), options trail (`phase:`, `free`, `curve:`).
3. The name "atom" for the non-param manifest kind.
4. Control-rate for Python-side LFO segment emission (proposal: ~30–50 Hz,
   matching the `/pt` streaming precedent).
5. Whether `stop` on a `free` LFO should be resendable-safe (it is — freeze
   is idempotent).
