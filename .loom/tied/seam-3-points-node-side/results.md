# seam-3-points-node-side — results (2026-07-11)

The S1 implementation: point geometry broadcasts on the LAN, every node
decomposes locally. Supersedes the reverted spatial-0 engine (salvaged its
falloff curves and path/orbit motion driver from `0ce8821`).

## What changed

- **`python/pointfield.py` (new, shared):** falloff curves keyed by the wire
  enum (0 linear, 1 smooth, 2 gauss), `/pt` wire parsing (frame `1+5n` args /
  sparse 5 args / `/pt/clear`), and `decompose(points, elements)` →
  `(pointId, element, value)` with **1-based element indices** (pair order,
  contract §5). Imported by helper.py, simfleet.py, and verifies — the real
  node and the fake fleet can't drift.
- **`python/helper.py`:** `NodeState.elements` (from the persisted
  assignment) + `points` field; `apply_assign` takes true-N `x y` pairs
  (old fixed `args[3:7]` retired); `/pt` plane handled selector-less before
  the `/os` gate; shaped scalars go to the engine as `/pt <pid> <el> <v>` on
  6661; removed/cleared points release with one `v=0`.
- **`dashboard/points.py` (new):** authoring math — ws payload sanitize,
  motion evaluation (static/path/orbit, the spatial-0 test driver), frame/
  sparse wire args. Falloff accepts names or wire ints.
- **`dashboard/osc_bridge.py`:** point state in `state.data["points"]`
  (runtime-only), 25 Hz `points_loop` that only broadcasts while a point
  moves (static set = one frame, silence = hold), sparse/clear senders,
  catch-up re-broadcast of the current frame after the params push (frame is
  selector-less, so "unicast" is an idempotent re-broadcast). `assign()` now
  takes an elements list (true N).
- **`dashboard/server.py`:** ws `set_points` / `set_point` / `clear_point`;
  `device_elements()` maps the UI's pos1/pos2 slots onto the wire pairs.
- **`tools/simfleet.py`:** devices keep `elements` in memory (assign +
  persisted state file), decompose `/pt` via the shared module, log
  `pt <pid> el<n> v=<value>` as the test surface; per-device drop applies to
  `/pt` like any broadcast.
- **`.notes/pd-edits-for-bob.md`:** A5/A6 updated from "pending ratification"
  to the live spellings (1-based element, release-to-zero).

## Decisions made here (flagged for review)

- ~~**Element index is 1-based** on the engine wire.~~ **SUPERSEDED
  2026-07-11: Bob ruled 0-indexing is the project default** (elements,
  points, all new indices — now a CLAUDE.md house rule). Flipped same-day
  across pointfield/helper/simfleet/contract §5/pd-edits A6; this stitch's
  verify re-run green (18/18) at 0-based.
- **Release semantics:** a point removed by clear/frame-diff sends one
  `v=0` per element so the engine doesn't hold a stale proximity. The wire
  itself stays pure full-state.
- A lone `pos2` (no `pos1`) becomes element 1 — the true-N wire can't
  express a gap; spatial-1's multi-element UI will formalize slots.

## Verification

    ~/.venvs/bopos/bin/python verify_points_node_side.py   # from this dir

18/18 checks. Part A imports the **real helper.py** in-process (sync-2
style; `set_hostname` stubbed, in-memory store) and drives
`handle_lan_datagram`: true-N assign → elements, frame/sparse/clear →
exact shaped scalars observed on a bound 6661 socket. Part B runs the real
dashboard + two simfleet instances + a SO_REUSEPORT sniffer: static set is
exactly one atomic frame; an orbiting point broadcasts ~25 Hz and **every**
sim-logged proximity equals `falloff(distance)` recomputed from the sniffed
geometry; sparse/clear wire shapes; a late-joining sim with a persisted
assignment gets the current frame + master via the params catch-up.

Hardware note: audible behavior needs Bob's PD receiver (`bopos.point`, A6/
B2) and a rig — simfleet is the test surface here, as the stitch specified.

## Follow-ups

- `spatial-audio/spatial-1` (authoring UI) builds on the ws surface
  (`set_points`/`set_point`/`clear_point`) and Bob's element-dot direction.
- `spatial-audio/spatial-2` (synced start) is unblocked now that this tied.
