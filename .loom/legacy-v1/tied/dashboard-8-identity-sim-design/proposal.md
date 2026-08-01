# Proposal: seats — device identity, binding, and dashboard-managed simulation (dashboard-8)

**Status: awaiting Bob's ratification.** From
`dashboard/dashboard-8-identity-sim-design`; source is Bob's 2026-07-13 brain
dump (`.lore/items/2026-07-13-composer-experience-brain-dump`). Facts from
two code surveys in the stitch dir (`survey-identity-state.md`,
`survey-simfleet-audition.md`) — every claim about current behaviour has a
file:line there.

## 1. The problem, precisely

`installation.json` conflates two things. A **device** row (keyed by uid)
carries both *runtime facts* (online, ip, version) and *the piece's
decisions* (id, name, positions, patch, params). Consequences, all observed
in code:

- You cannot author a position or an ID before a device exists — there is
  nowhere to put it (`set_position` refuses unknown uids,
  `server.py:210-212`).
- Devices accumulate forever — no code path removes a row, hence the jq
  surgery to forget five simfleet + three audition uids.
- Sim devices are indistinguishable from real ones (no kind/origin field
  anywhere; any well-formed `/hb` persists a row).
- Swapping a dead Pi means re-typing its identity onto a new uid.

## 2. The model: seats and devices

Split `installation.json` into two collections:

**A seat is a place in the piece.** Authored by the composer, exists before
any hardware, fully durable:

```json
"seats": {
  "0": { "id": 0, "name": "porch", "positions": [[1.2, 0.4], [2.0, 0.4]],
          "patch": "demo-pd", "params": {"gain0": 0.8},
          "bound": "b8:27:eb:xx:xx:xx" }
}
```

Everything the piece cares about — id, name, element positions (true-N
ready; UI keeps two slots for now), patch, param values — lives on the
seat. `bound` is the uid of the device currently sitting in it, or null.

**A device is a box that heartbeats.** The roster keeps only identity and
runtime facts: uid, hostname (see §5), last_seen, ip, version, plus
`virtual: true` for simulation-spawned instances. No piece data.

**Binding** a device to a seat fires the existing
`/all/os/assign <uid> <id> <name> [x y]×N` with the *seat's* data — the
wire contract is untouched; the node-side experience is identical.
Unbinding frees the seat; the seat keeps everything. **Device swap = bind
the replacement to the same seat. Pre-arranging the space = authoring seats
with no bindings.** Both of Bob's asks fall out of the same split.

## 3. Simulation: one toggle, seats inhabited

**Simulate ON**: the dashboard spawns and manages `tools/audition.py` as a
child process — one engine instance per seat that has **no live bound
device** — and binds each instance to its seat (ordinary `/os/assign`;
audition instances already accept exactly this). Instance rows enter the
roster flagged `virtual: true`, never persisted. The listener puck renders
**only while simulation is active** (it drives the loopback-only
`/audition/listener` preview seam, which is meaningless otherwise).

**Simulate OFF**: stop the relay, drop the virtual rows and bindings.
Seats are untouched — which is why "save the sim fleet state" needs no new
mechanism: **the seats are the sim fleet state**, and they're already what
venue save/load captures.

Seats whose bound real device is live are not doubled by default (the room
is already playing them); a per-seat "simulate anyway" override can come
later if headphone preview of a live rig turns out wanted (Q3).

Occupancy renders on the map and sidebar: each seat is **live** (real
device bound + online), **sim** (virtual instance), or **empty** (silent).
simfleet stays what it is — a protocol-load dev tool driven from the CLI;
the composer-facing Simulate toggle is the audible audition rig
(`--audio-backend none` remains available under the hood, Q2).

## 4. Forgetting

- `forget_device <uid>` (ws): removes a roster row; if bound, unbinds first
  (seat keeps its data). Confirm-gated when the device was seen recently.
- **Forget all offline unbound** — one bulk action; this is the jq surgery
  as a button.
- Virtual rows are auto-forgotten on Simulate OFF and never written to disk,
  so the `02:53:49:4d:*` / `audition-*` accumulation cannot recur.

## 5. One wire addition: hostname

Hostname never crosses the wire today (not in `/hb`, not in `/os/report`),
so ui-0's "suggest name from hostname" is impossible as-is. Additive
amendment: **`hostname` joins the `/os/report` JSON** (contract §6 report
fields; heartbeat stays lean). Recorded additively per the delegated
wire-shaping rule. When a device is bound to a fresh seat, the suggested
seat name = its reported hostname.

Everything else is dashboard-local: no new fleet verbs for seats, binding,
or simulation. The contract's identity model (§5) is untouched — seats are
the dashboard's own "persistent uid → assignment table" made first-class.

## 6. The composer walkthrough (the UX this buys)

1. **Pre-production, no hardware:** set the room, click the map to add
   seats (next free id, 0-indexed), name them, drag or type positions
   (ui-3). Hit **Simulate** — every seat comes audible on the laptop, the
   listener puck appears, compose on headphones. Save as a venue file.
2. **Deploy day:** real Pis heartbeat in and appear as unbound devices in
   the sidebar. For each seat: bind → pick a device (hostname shown). The
   seat's id/name/positions/patch/params push down in one assign. A dead
   Pi's replacement is a rebind, not a re-setup.
3. **Re-rig at a venue:** load the venue; seats remember their last uid, so
   any remembered device that heartbeats is auto-rebound (Q5); the rest is
   bind-by-hand from the seat list.

## 7. Migration

On first load of the old schema: every device with `id >= 0` lifts its
id/name/pos1/pos2/patch/params into a new seat bound to that uid; the
device row keeps only identity/runtime. Unassigned rows stay as unbound
roster entries (candidates for the bulk forget). A `schema` version field
goes into `installation.json`. Venue files migrate the same way on load.
simfleet needs nothing — assignment still arrives by `/os/assign`.

## 8. Effect on existing loom work

- **ui-0-sidebar-fixes** (hostname suggestion) gains its missing wire fact
  from §5 — the report field lands with this design's node-side child (or
  rides `dist-2-node-side` if that's worked first; coordinate, one change).
- **ui-2-spatial-map-pass** — listener-puck *visibility* rule lands here as
  designed (sim-only); ui-2's drag-dial applies whenever the puck shows.
- **dashboard-6-rig-adoption** — unchanged; this design should make the
  real-rig adoption easier, not gate it.
- **dist-3-dashboard-send** — patch dropdown targets a *seat's* patch field
  when both land; sequencing note, no conflict.
- Implementation children (created on ratification, deferred like dist-1..4):
  1. `d8-1-seat-model` — state schema, migration, forget (single + bulk),
     ws surface, venue save/load.
  2. `d8-2-simulate-toggle` — relay child-process management, virtual rows,
     puck visibility, occupancy states.
  3. `d8-3-binding-ux` — seat authoring on the map, bind/unbind flows,
     sidebar restructure (seats + unbound devices + simulate section),
     hostname suggestion, auto-rebind on venue load.

## 9. Open questions — Bob's to answer

- **Q1 the noun:** "seat"? (alternatives: station, post, spot, voice —
  "role" is burned). The word will be all over the UI and code.
- **Q2 sim flavours:** Simulate toggle = audible audition rig only
  (recommended; simfleet stays a CLI dev tool) — or expose a
  protocol-only/silent mode in the UI too?
- **Q3 sim scope:** skip seats with a live bound device (recommended) — or
  simulate everything always, or per-seat override now?
- **Q4 forget gating:** confirm-gate only when recently seen (recommended)
  — or always confirm?
- **Q5 auto-rebind:** on venue load, a remembered uid that heartbeats
  rebinds automatically (recommended) — or always confirm by hand?
- **Q6 hostname in `/os/report`:** ok as the additive wire change?
