# Seed — the problem as Bob framed it (2026-07-10)

The instigating event: the `spatial-0` engine gave bopOS responsibility that
belongs to the patch, and Bob sees "more coupling than is required" across the
system. This session re-draws the **responsibility seam between bopOS and a
patch** (PD is the reference engine; SC, openFrameworks, and others must be
equal citizens). It takes the S1 node-side points draft as an input but looks
one level up.

## 1. The candidate principle: provided, not enforced

OSC addresses that bopOS provides **can be subscribed to by the patch, but
this isn't enforced.** Examples in Bob's words:

- There should be a **master-gain** value that bopOS *provides* and a **gain**
  param that bopOS *provides*, "but the implementation is entirely enacted
  within the patch." (Today the dashboard multiplies master into the volume
  param before it hits the wire — ground-truth #6 — so the patch never sees
  master. Under the principle, master would be its own provided message the
  patch multiplies in itself.)
- **Points** are OSC messages sent from bopOS "that can be picked up in the
  patch."
- The **one candidate exception is mute**: a safety issue that "should be able
  to operate independently of the engine if at all possible."

The council should test the whole current surface against this principle and
say what bopOS provides, what it enforces, and why — and how much of the
current design (contract text and code) needs to change.

## 2. Facilitator promotion (per patch)

Real facilitator dashboards (previous installations) have carried a **custom
set of controls specifically chosen for the patch** — a subset of the patch's
controls — plus **bopOS commands** (shutdown, reboot, update patch, …). The
design so far only has volume cards + master + SILENCE ALL, driven by the
manifest `role:"volume"` marker. Wanted: a way to **mark or promote certain
OSC messages/params to the facilitator dashboard, per patch.** (Note the
ratified facilitator scope guard currently excludes admin verbs —
ground-truth #9 — the council should take a position; Bob arbitrates.)

## 3. Multiple elements per device

A device's audio channels may need to run **an independent patch instance
each, each with its own position** (Belief System: two per Pi, L/R). Kite
Choir and Playable Streets are stereo single-element devices, but
multi-element is a likely future need and could be used in Playable Streets
if available.

- Simplification allowed: assume each element runs **the same patch** if that
  helps; keep different-patches-per-element open only if it's nearly free.
- Explicit question: **how much complexity does this add to the dashboard?**
  Does multi-element need to be a separate *mode* of the dashboard or of
  bopOS as a whole?

## What the session must produce

How the seam should be drawn; what needs to be reconsidered in bopOS; **how
much of a redesign we're looking at.** Depth: principles plus concrete
sketches (wire shapes, manifest shapes) so the judgment is buildable — but PD
receiver conventions and final spellings stay flagged for Bob's co-design at
ratification. Multi-element: design the element model so it lands additively,
and stage what ships now vs. later.
