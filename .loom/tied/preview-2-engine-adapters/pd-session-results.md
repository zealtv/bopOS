# PD adapter session results — 2026-07-13

Bob edited and tested `pd/bopos.pd`; agents inspected and guided the work but
did not edit any `.pd` file.

## Edit

The selector-stripped local engine ingress now dispatches top-level
`audition` beside `id` and `os`, then routes member `matrix` to the existing
private send:

```text
netreceive -> oscparse -> list trim
  -> route id os audition
  -> route matrix
  -> s bopos-audition-matrix
```

The unmatched top-level outlet still feeds the unchanged
`route p pt cue notify` patch/provided-term paths. Unknown audition members are
discarded rather than leaking into ordinary routes.

## Real engine-port verification

With the default patch running and listening on selector-stripped localhost
port 6661, Bob sent real OSC UDP frames using `pythonosc.udp_client`:

- `/audition/matrix 0.92388 0.382683 0 0.541196` moved the image to the
  expected left-of-centre position.
- A malformed two-value `/audition/matrix 0 0` retained that last valid image.
- A first symbol atom was rejected by the typed unpack, and symbol atoms in
  matrix positions 2, 3, and 4 were each rejected after Bob added the
  four-value `-1` sentinel reset. Every malformed frame retained the complete
  last-valid identity matrix; none partially changed the output.
- `/audition/matrix 1 0 0 1` restored exact identity behavior.
- `/os/master 0.5` halved production level smoothly and `/os/master 1` restored
  it, proving the existing master route remains intact.
- `/notify identify` still produced the notification chirp.

The remaining `/id`, `/p`, `/pt`, and `/cue` graph spellings and connections
are retained by the focused static gate. No new public abstraction or inlet was
introduced; `bopos.out~` remains the public fixed-stereo boundary.

The validator now resets all four `[unpack f f f f]` values to an invalid
sentinel before each candidate. This prevents a wrong-type atom in a cold
inlet from reusing a stale coefficient while preserving the existing exact
arity, finite/range, last-valid, and 20 ms smoothing behavior.
