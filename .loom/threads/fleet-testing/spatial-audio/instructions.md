# spatial-audio

**Goal:** move sound through space across the fleet, Belief-style — the
dashboard broadcasts moving points, each device turns them into per-element
proximity, the patch maps that to sound.

**Status:** software built and tied (points on the wire, node-side
decomposition, map authoring, synced start). Left:

- `northern-broadwalk-site-plan` — **ready.** Turn the Kite Choir 52-position CSV
  into a loadable venue.
- `spatial-3-rig-sweep` — waiting, needs a real fleet.

**Done when:** a sound sweeps audibly across a real multi-Pi installation,
authored from the dashboard map and decomposed on the nodes.

## Model (ratified 2026-07-10, patch-seam council)

The dashboard broadcasts point geometry (`/pt`, any number of points). Each
device computes per-element proximity 0→1 locally. The patch decides what to do
with it. bopOS never writes into a patch parameter. Authority:
`.loom/legacy-v1/tied/seam-0-council/`.
