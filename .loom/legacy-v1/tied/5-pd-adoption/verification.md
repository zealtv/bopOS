# 5-pd-adoption — verification

**Tied 2026-08-01 on Bob's call.** Bob: *"that's tested on pd locally. good
enough."*

## What was verified

The `.pd` receiver edits were made by Bob (house rule: agents never edit `.pd`)
against the note child `3` left in `.notes/pd-edits-for-bob.md` — `/e/<identity>`
routed alongside the retired `/cue` in `pd/bopos~.pd` and
`pd/babs.blineseq.pd`, taking up to three floats, nested identity preserved.

Exercised in **Pure Data locally**. A real PD patch receives `/e/<identity>` and
acts on it, which was the substantive question: the wire form `3-event-plane-wire`
shipped is the one PD actually consumes.

## What was NOT run, and is therefore not claimed

The stitch's instructions asked for a four-part check on the **Finn Jet + Ciro
Toast** two-device rig. Local PD covers the first part only. Not run:

* arity 0 / 1 / 2 / 3 all arriving intact across the rig;
* **forward-sync timing across two devices** — the thing cues existed for, and
  the one property a single local instance cannot demonstrate at all;
* the `"0"` fire-on-arrival sentinel landing with no audible scheduling delay.

Bob accepted the local result as sufficient to tie rather than hold the thread
open on rig availability. Recorded here so a later reader does not mistake this
for a completed rig check — per the stitch's own instruction, *do not tie a
hardware claim on a software gate*. The two-device forward-sync behaviour
remains unmeasured on hardware.

Cue-id renaming in Bob's out-of-repo patches: the in-tree scan found nothing to
rename, and Bob's own patches were his to sweep.
