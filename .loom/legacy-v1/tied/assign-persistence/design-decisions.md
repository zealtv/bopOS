# assign-persistence — design decisions (2026-07-07)

Contract §5 (assignment, boot resolution), §10 (persistence store), §4
(unicast replies), §1 (legal empty answers). Builds directly on hb-identity's
NodeState, LAN listener, and heartbeat thread.

## 1. Store layer (`python/store.py`, used by helper.py)

- File-backed KV: one file per key under `$BOPOS_DIR/state/store/<key>`,
  JSON list of values (str/int/float survive round-trip). Atomic writes
  (tmp + `os.replace`) — a power cut mid-write must not eat the assignment.
- Keys are validated `[A-Za-z0-9._-]+` (they become filenames); anything else
  is rejected with a loud print and ignored — fail loud, not silent.
- **`update_model`** comes from node `bopos.config` (`UPDATE_MODEL`,
  default `persistent`). Ephemeral hosts get the same store API backed by a
  RAM dict only (§5: they sacrifice persistence, re-assigned each boot —
  an accepted adaptation). The flag will surface in `/os/report`
  (patch-manifest stitch).
- Missing key → empty list. Empty is always a legal answer (§1).

## 2. `/all/os/assign <uid> <id> <name> [posx posy pos2x pos2y]`

- New member on the existing 6660 LAN listener. uid must equal ours, else
  ignore silently (every node hears the broadcast; one applies it).
- Apply, in order: `node_state.id = int(id)`; hostname change to `<name>`
  (same hostnamectl/hosts/avahi dance as `/config` — extracted into a shared
  `set_hostname()`); tell the engine via the existing `/id` message on 6661;
  persist store key **`assignment`** = `[id, name, posx, posy, pos2x, pos2y]`
  (positions only if given); **ack by heartbeating the new id immediately** —
  the heartbeat thread now waits on a `threading.Event` instead of `sleep`,
  and assign sets it (also flips the 2 s discovery cadence off in the same
  beat).
- Idempotent full-state: re-applying the same assign is a no-op-shaped write;
  a different assign for the same uid simply overwrites (§4 law).
- Positions are persisted but not otherwise consumed yet (dashboard/spatial
  stitches read them later; the engine can `/os/load assignment`).

## 3. Boot resolution (contract §5, verbatim order)

`resolve_id`: store `assignment` key → `bopos.devices` seed by uid → −1.
The hb-identity fast-heartbeat behaviour already covers
unassigned-and-announcing; the old unknown-MAC-goes-silent failure is
formally dead (bopos.devices is a seed, never a gate).
Hostname is NOT re-asserted at boot — hostnamectl already persisted it when
the assign was applied.

## 4. `/os/store` and `/os/load` (§10)

- LAN grammar on the 6660 listener: `/<sel>/os/store <key> <values…>`
  persists; `/<sel>/os/load <key>` replies **`/os/load <key> <values…>`
  unicast to (src, 5550)** — request/reply is never broadcast (§4). Missing
  key replies with just the key (legal empty).
- Localhost handlers `/store` and `/load` registered on the 7770 server so
  the engine path works the moment Bob routes `store`/`load` in PD
  (`/load` replies to PD on 6661 as `/load <key> <values…>`); noted in
  pd-edits-for-bob.md as an observation — the PD-side plumbing design
  (keeping load replies off the LAN forward) is Bob's.

## 5. uid pinning — deliberately NOT done

An assign does not write `state/uid`. Pinning would break the §13 uid==MAC
guarantee after a hardware swap (SD card moved to a new Pi would carry the
old identity). `state/uid` stays an operator/live-image hook, as decided in
hb-identity.

## 6. simfleet (same-stitch protocol rule)

- v1 devices handle `assign`: matching MAC applies id + hostname, acks with
  an immediate `/hb` at the new id, drops to the slow cadence.
- **`--state-dir <dir>`**: per-device assignment JSON (`<mac>.json`, colons
  → `-`) so the instructions' loop is honestly testable: assign → kill the
  dashboard listener → restart the *simfleet process* → devices boot from
  persisted assignment with no dashboard present. Default off = today's
  in-memory behaviour.
- **`--ephemeral N`**: last N devices never persist and boot unassigned every
  run even with `--state-dir` (update_model: ephemeral).
- Boot resolution mirrors the node: state-dir assignment → seeded id
  (devices-file / generated, or −1 if `--unassigned`) → −1.

## Out of scope (parked where)

- Dashboard's own uid → assignment table, re-setup UX → dashboard-3.
- `/os/report` exposing update_model → patch-manifest.
- PD-side store/load routing and engine-side persistence migration (§10
  "PD-side state that persists today migrates here") → Bob + a later stitch.
- Hardware verification → needs Bob or a live rig.
