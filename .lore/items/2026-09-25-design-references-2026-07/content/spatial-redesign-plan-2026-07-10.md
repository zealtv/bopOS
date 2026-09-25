# Spatial audio — redesign plan (2026-07-10)

Resolution plan after Bob flagged that the `spatial-0` engine built on
2026-07-09 uses the wrong model. Captures the session record, the agreed target
model, the design sessions needed before implementation, and the revert list.
**Nothing here is executed yet — awaiting Bob's go on §5–§6.**

## 1. What we built this session (the record)

`spatial-0-engine` tied 2026-07-09 (commit `0ce8821`; session closed by
`9e476e6`). Verified 18/18 (`.loom/tied/spatial-0-engine/verify_spatial_engine.py`).

Model as built:
- **Dashboard** computes each device's spatial gain from a **single** point and
  its `installation.json` position, and streams per-device `/p/gain` at ~25 Hz.
- The scalar is multiplied into the device's **volume param**
  (`volume_param()` → role `volume` / literal `gain`), composed as
  `stored × master × spatial` inside `send_device_param`.
- Runtime-only singleton config in `state.data["spatial"]`, driven by a
  `set_spatial` ws command; `static`/`path`/`orbit` motion.

Files touched: `dashboard/spatial.py` (new), `dashboard/osc_bridge.py`,
`dashboard/server.py`, `dashboard/state.py`, `tools/simfleet.py`,
`dashboard/README.md`, `CLAUDE.md` (venv heal — unrelated).

## 2. Why it's the wrong model (agreed 2026-07-10)

1. **Altitude / bandwidth.** The dashboard pre-computes and streams per-device
   parameters. The right model is **node-side**: the dashboard broadcasts point
   *geometry* (small, whole-fleet) and each device decomposes it locally. This
   is what the contract had filed as the deferred "Stage B" (`/pt`); it is
   actually the primary model, not a later optimisation.
2. **Sink.** Spatial rides the patch's **volume slider**. It should drive a
   flexible **"point parameter"** the patch consumes and maps itself — usually a
   sample's gain, sometimes a filter cutoff or other param — patched *upstream*
   of the patch's own volume. bopOS must not hardcode it to volume.
3. **Cardinality.** Singleton point. We need an **arbitrary** number of points
   (Belief System used 5).
4. **Composition.** Tangled into the facilitator's master/VCA model. Spatial is
   **orthogonal**; the facilitator role is parked entirely for now.

## 3. Target model (decisions locked this session)

- **Points are moving sound sources.** Arbitrary count. Each point =
  `position (x,y) + radius + falloff` (deliberately not over-prescriptive; a
  point carries **no independent level** for now — source amplitude lives in the
  patch).
- **Dashboard broadcasts point geometry** for the whole fleet (low bandwidth) —
  no per-device pre-calculated parameter streams.
- **Each device decomposes ALL points locally** (simplest binding for v1). For
  each point, `helper.py` computes a **proximity scalar 0→1** from the device's
  own position — **bopOS owns the radius + falloff math** (dividing line = "A":
  patch receives a shaped 0→1 value, not raw geometry; expose **raw distance**
  as an option later). The **patch chooses** which point(s) it consumes (by
  receiver name) and maps the scalar wherever it likes, upstream of volume.
- **The sequencer will drive the points** (later). Until then, point authoring
  is minimal / programmatic. This layer is the **primitive** the paused
  scene-sequencing thread will address.
- **Device = element = one position today** (fine for Kite Choir). **Split
  channels** — multiple positioned elements per device (Belief ran L/R as two
  positioned patches per Pi) — are a likely later stage. Identity must not
  preclude it. Terminology: **device** = the Pi/computer; **element** = a
  positioned channel.

## 4. Open design questions → sessions needed before implementation

### Session S1 — point wire + node-side decomposition (co-design with Bob; PD)
- `/pt` broadcast shape: per-point `id, x, y, radius, falloff`; update cadence;
  reconcile with contract §4's "broadcast is scarce/lossy" discipline (idempotent
  full-state per frame is loss-tolerant — good).
- `helper.py` decomposition: point + own position → proximity 0→1; **how the
  value reaches PD** (localhost OSC, receiver naming, e.g. `/pt/<n>`); what a
  **"point parameter"** looks like from the patch side; whether the manifest
  declares anything (contract §8 `role`) or the patch just listens by name.
- Simulator: `simfleet` must decompose points too (node-side feature lands in
  the sim in the same stitch) so spatial stays testable without hardware.
- **Salvage:** the falloff curves in `dashboard/spatial.py`
  (`linear`/`smooth`/`gauss`) move node-side largely intact.
- **Output:** a written proposal + a **contract §4 amendment** (overturn the
  "dashboard-computed `/p/gain` is the correct first implementation" framing;
  node-side `/pt` becomes primary). This is a ratify-gate.

### Session S2 — addressing / identity (device vs element)
- Bob flagged this as a **more significant rework needing design thought.**
- Should spatial/positions key on **element** rather than device? How does a
  device declare 1..N positioned elements? Impact on assignment/persistence
  (contract §5), uid/heartbeat, and the dashboard's position model.
- Recommend S2 **follows** S1: S1 unblocks a working node-side prototype at
  1 element/device; S2 makes split-channel additive rather than a rewrite.

## 5. Revert / salvage (proposed — awaiting Bob's go)

Recommend removing the wrong-model implementation from the working tree so no
later stitch (spatial-1/2) builds on it, **keeping two incidental goods**:

- **Revert:** `dashboard/spatial.py`; the spatial factor + tick loop +
  `set_spatial` in `osc_bridge.py`; `set_spatial` in `server.py`;
  `state.data["spatial"]`; the "Spatial automation" section in
  `dashboard/README.md`.
- **Keep:** the `CLAUDE.md` venv heal (unrelated, good); `simfleet`'s p-plane
  logging (harmless, useful); the tied `spatial-0-engine` stitch dir as the
  historical record (annotate its `results.md` "superseded — see this plan").
- **Salvage into S1:** the falloff curves; the point-motion (`path`/`orbit`)
  logic is reusable dashboard/sequencer-side for *driving* points.

Everything reverted stays recoverable from git (`0ce8821`) and the tied stitch.

## 6. Loom changes (after ratification)

- Rewrite the `spatial-audio` parent's Stage A/B language.
- Add design-session stitch(es), `.waiting` on Bob: **S1** (and later **S2**).
- Re-scope children: `spatial-1` (was "dashboard drag-a-gain-point UI" →
  becomes "author/move points"); `spatial-2` (synced sample start via `/cue` —
  still valid, complements). Mark `spatial-0` **superseded**.

## 7. Recommended immediate next actions

1. Bob confirms this plan (esp. the §5 revert list and the S1-then-S2 split).
2. I execute the revert (keeping the two goods), annotate the tied stitch, and
   restructure the loom (add S1/S2 as `.waiting`, re-scope spatial-1/2, mark
   spatial-0 superseded).
3. Run **S1** as a design session (council or co-design with Bob — it touches PD
   receivers and the contract).
4. After S1 ratifies: implement node-side decomposition (`helper.py` + `simfleet`
   + `/pt`) and land the contract §4 amendment.
