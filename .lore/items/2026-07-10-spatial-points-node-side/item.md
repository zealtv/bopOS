# Spatial points — node-side decomposition (design draft)

Design draft for bopOS spatial audio, written after the 2026-07-09 `spatial-0`
engine was found to use the wrong model (dashboard-computed per-device gain into
the volume slider, single point). Bob's target model: the dashboard **broadcasts
point geometry** (an arbitrary number of moving sound-source points, each
`position + radius + falloff`) and **each device decomposes all points locally**
— `helper.py` turns each point + the device's own position into a **proximity
scalar 0→1** (bopOS owns the falloff math; raw distance an option later) and
hands it to the patch as a flexible **"point parameter"** the patch maps itself
(gain, filter, …), upstream of the patch's own volume. Spatial is orthogonal to
the facilitator/VCA model (parked). The sequencer will drive the points later;
this is the primitive beneath it.

This is a **draft to run a design session from**, not a ratified proposal. It
sketches a candidate `/pt` wire shape, the Python/PD dividing line, the
simulator plan, and a contract §4 amendment, and lists the questions that need
Bob (PD receivers) and possibly a council. The device-vs-element addressing
rework (split-channel) is called out as a **separate later session (S2)**.

## Source

Interactive design conversation with Bob, 2026-07-10, after the autopilot
`spatial-0-engine` stitch (tied 2026-07-09, `0ce8821`, now reverted from the
working tree and marked superseded). Companion working plan:
`.notes/spatial-redesign-plan-2026-07-10.md`. Loom: staged review stitch
`spatial-audio/spatial-0b-redesign-review` (`.waiting` on Bob).

## Outcome

Awaiting a decision on session format (council vs interactive co-design) and
then ratification. Read `content/draft.md`.

## Tags

bopos, spatial-audio, osc-contract, node-side, design-draft, decision-gate,
scene-sequencing
