# 5-pd-adoption

The engine side and the rig check. **Bob's stitch** — the house rule is
absolute: agents never edit `.pd` files.

Two patches receive `/cue` today and need `/e/<identity>` receivers taking up
to three floats:

- `pd/bopos~.pd`
- `pd/bop/babs/babs.blineseq.pd`

Child `3` writes the exact receiver change into `.notes/pd-edits-for-bob.md`.
An agent may prepare that note, read the patches, and describe the change; it
may not make it.

Also here: any cue ids inside Bob's own patches outside this repo. The address
grammar is narrower than the old `cueId` (`[A-Za-z0-9_-]+` segments vs
`[^\x00\r\n]{1,64}`), so an id with spaces or punctuation needs renaming. The
repo scan found nothing to rename in-tree; Bob's patches are the only
exposure.

## Hardware adoption check

Software children `2`–`4` tie on software gates. What remains genuinely
unverifiable without hardware, on the Finn Jet + Ciro Toast rig
([[finn-ciro-test-rig]]):

- a real PD patch receiving `/e/<identity>` and acting on it;
- arity 0 (the old cue case), 1, 2, and 3 all arriving intact;
- forward-sync timing across two devices — the thing cues existed for;
- the `"0"` sentinel firing on arrival with no audible scheduling delay.

State the result plainly in `verification.md`. If only part runs, say which
part — do not tie a hardware claim on a software gate.
