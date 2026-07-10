# Spatial points — node-side decomposition (design draft)

Status: **draft for a design session.** Proposed pieces are marked
**[proposed]**; things that need Bob / co-design or a council are **[open]**.

## 1. Model (agreed 2026-07-10)

- **A point is a moving sound source.** Arbitrary count (Belief System ran 5).
  Each point = `position (x,y) + radius + falloff`. No independent level — a
  point is geometry; source amplitude lives in the patch.
- **Dashboard broadcasts point geometry** for the whole fleet. Low bandwidth:
  one small full-state message set per frame, not per-device pre-computed
  parameter streams.
- **Each device decomposes all points locally.** `helper.py` computes, per
  point, a **proximity scalar 0→1** from the device's own position and the
  point's radius+falloff. bopOS owns the falloff math (dividing line "A"; raw
  distance can be exposed later as an option).
- **The patch is the sink.** The patch consumes the point value(s) by name and
  maps them itself — usually a sample's gain, sometimes a filter cutoff or other
  param — patched **upstream** of the patch's own volume. bopOS never hardcodes
  the target to volume.
- **Orthogonal to the facilitator/VCA** volume model (parked).
- **Sequencer drives points** later; this layer is the addressable primitive.
- **Device = element = one position today.** Split-channel (multiple positioned
  elements per device) is a later stage — see §7 (S2), don't preclude it.

## 2. Wire shape [proposed — the core question for the session]

Broadcast, full-state per frame, loss-tolerant (idempotent, so a dropped frame
self-heals on the next — fits contract §4's "broadcast is scarce/lossy"
discipline). Absolute time stays out of it; floats are fine (positions are
low-precision metres, well within PD's 32-bit — unlike the §3.1 clock values).

Two candidate encodings to decide between:

- **A. one message per point** (simple, sparse-update friendly):
  `/pt <pointId> <x> <y> <radius> <falloff>` — where `falloff` is a small enum
  int or short string. A point is removed with an explicit
  `/pt/clear <pointId>` (or a level/enabled flag).
- **B. one message per frame, all points** (atomic frame, fewer packets):
  `/pt <n> <id0> <x0> <y0> <r0> <f0> <id1> …` — the whole point set in one
  datagram; a point absent from the frame is gone. Bounded by MTU (~fine for
  dozens of points).

Recommendation to discuss: **B** for the moving-frame case (atomicity: all
points advance together, matching a sequencer tick), with a per-point sparse
form for authoring edits. Cadence ~20–30 Hz while moving; nothing sent when
still (idempotent, so silence = hold).

**[open]** exact spelling, enum vs string for falloff, per-point vs per-frame,
whether radius/falloff are per-point on the wire or a patch-side constant.

## 3. Python ↔ PD dividing line [proposed]

- `helper.py` receives `/pt` on the LAN (6660 alongside the other dash→fleet
  traffic), keeps the current point set, and on each frame (or each point
  update) computes proximity for the device's own assigned position:
  `proximity = falloff(distance(devicePos, pointPos), radius)` in [0,1].
- It forwards each point's value to PD over localhost as a **named point
  parameter**. **[open]** the receiver convention — candidates:
  `/pt/<pointId> <value>` (patch has `[r /pt/0]` etc.) or a single
  `/pt <pointId> <value>` the patch routes. The patch chooses which point ids
  it listens to; unlistened points cost nothing.
- **Falloff library salvage:** the `linear` / `smooth` (smoothstep) / `gauss`
  curves from the reverted `dashboard/spatial.py` move into a small node-side
  module used by both `helper.py` and `simfleet`.
- **PD side is Bob's** (house rule: agents never edit `.pd`): the receiver(s),
  and wiring the 0→1 value to gain/filter/etc. upstream of volume. bopOS's job
  ends at delivering the named scalar.

**[open]** does the manifest need to *declare* point parameters (contract §8
`role`, e.g. `role:"point"`), or does the patch just listen by name with no
declaration? Declaration would let the dashboard show which points a device
renders; listening-by-name is simpler. Lean: **no declaration for v1**, revisit
if the UI needs it.

## 4. Simulator plan

`simfleet` gains the same node-side decomposition (a fake Pi must render points
to stay a useful test vehicle without hardware). It already knows each device's
position; add: parse `/pt`, compute proximity per point from the shared falloff
module, and **log** the resulting per-point value (as it now logs `p/<name>`) so
a `verify_*.py` can assert `proximity == falloff(distance)` over a moving frame
— the same style as the reverted spatial-0 verify, but reading node-computed
values instead of dashboard-computed ones. Protocol-only and audible instances
stay config-compatible.

## 5. Contract §4 amendment [proposed]

§4 currently says dashboard-computed per-device `/p/gain` is the "correct first
implementation" and files node-side `/pt` as a deferred Stage B. **Overturn
that:** node-side `/pt` decomposition is the **primary** model (bandwidth +
flexibility + arbitrary points). Record the dividing line (bopOS emits a shaped
proximity; patch maps it), the wire shape chosen in §2, and that the value is a
generic "point parameter," not gain. Keep the transport discipline (broadcast,
idempotent full-state).

## 6. What we are NOT deciding here

- **Point authoring UI** (drag/move points on the map) — a re-scoped
  `spatial-1`, after this lands. Until then points are driven programmatically /
  by a test driver.
- **Sequencer integration** — the paused scene-sequencing thread; this is just
  the primitive it will address.

## 7. Deferred: addressing / identity (S2) [open — separate session]

Bob flagged **device vs element** as a bigger rework needing its own design
thought. Today: device = element = one position. Split-channel means a device
runs N positioned elements (Belief ran L/R as two positioned patches per Pi).
Questions for S2: does spatial key on element? how does a device declare 1..N
positioned elements? impact on assignment/persistence (contract §5), uid, and
the dashboard position model. Recommend S2 **after** S1 so a 1-element/device
prototype ships first and split-channel lands additively.

## 8. Questions to settle in the session

1. Wire shape: per-point (A) vs per-frame (B) vs both; falloff enum spelling;
   radius/falloff on the wire vs patch-side.
2. PD receiver convention for the named point value (Bob's domain).
3. Manifest declaration of point params: yes/no for v1.
4. Whether bopOS also exposes raw distance now or later.
5. Session format for S1 itself: council vs interactive co-design (this draft is
   the input either way).
