# 4-contract-amendment

Write the OSC contract amendment that falls out of `1`, `2` and `3`. Written
last, from ratified rulings — not in parallel with them.

The wire is Bob's to ratify. This stitch proposes the text; the stitch that
implements each part carries it into code.

## What is known to be in scope

- **§5's definition sentence** is the thing being amended: *"**device** = the
  computer (one uid, one heartbeat, one engine instance); **element** = a
  positioned output the patch drives."* One engine instance per device is
  stated as fact throughout the section.
- **The assignment verb** `/all/os/assign <uid> <id> <name> [x y]×N` and its
  idempotent-full-state guarantee, plus `/all/os/to <uid> unassign` and its
  `-1` tombstone.
- **The heartbeat** `/hb <uid> <id> …` and its double role as discovery and
  assignment ack.
- **§4 Ports** — `docs/PORTS.md` says "the six ports" and both files describe
  6661/6662 as singletons. Whatever `2` rules about port allocation lands
  here and in `docs/PORTS.md`, which is a quick reference over this contract
  and must not drift from it.
- **Groups** (§5 seat-group membership) if `1` moves membership to the
  instance.
- **`/pt <point> <element> <v>`** (§4.1) if `1` changes what an element index
  means.
- **The engine surface §4.2** if an instance needs to learn its own identity,
  port, or channel assignment at launch — note that run context is
  launch-delivered by design and never sent over OSC.

## Constraints that do not move

- **PD float precision**: 32-bit, nothing needing >6 significant figures.
- **0-indexing** for elements, slots, and any new index, on the wire and in
  the data model.
- The contract records a **revision history** (§15); this amendment gets an
  entry naming the thread, at whatever version is then current (v1.17 as of
  2026-08-16).
- Additive where it can be; where it is a hard break, say so plainly and say
  what breaks — `44-event-plane/4-cue-retirement` (v1.15) is the house
  precedent for taking a clean break over a compatibility shim, and
  `58`'s Ciro Toast and Finn Jet incidents are the standing reminder that a
  manifest or grammar hard break reaches the field **at the speed of patch
  distribution**, as a crash-loop rather than a warning.

## Deliver

The proposed amendment text, section by section, in `proposal.md`. Then mark
`.waiting` and surface it.
