# spatial-audio

**Goal:** spatialise sound across the device fleet the way Belief did on Happy
Brackets: start a sound simultaneously on all devices (synced clock — done,
`clock-sync`), then move points through the space; each device decomposes each
point → a patch parameter = falloff(distance, radius).

**Model ratified 2026-07-10 by the patch-seam council** (authority:
`.loom/tied/seam-0-council/judgment.md` + `ratification.md`; the old Stage A/B
framing is dead — Stage A was built as `spatial-0`, reverted, and overturned):
the dashboard broadcasts point geometry (`/pt`, arbitrary count); each device
decomposes all points locally into per-element proximity scalars 0→1; the
patch maps them wherever it likes, upstream of its own volume. bopOS never
composes into a patch param (§1 seam law once seam-1 lands).

**Implementation lives in the `patch-seam` thread:** `seam-1` (contract
amendment gate, Bob) → `seam-3-points-node-side` (helper + simfleet + wire) →
then here:

- `spatial-1-authoring-ui` (`.waiting`) — author/move the point set on the
  dashboard map; re-scoped 2026-07-10; requires `seam-3` tied.
- `spatial-2-synced-start` — synced sample start via `/cue`; still valid,
  independent of the points work.

Done when: a sound sweeps across a real multi-Pi installation, authored from
the dashboard map, decomposed on the nodes.
