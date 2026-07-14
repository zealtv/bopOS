# d8-1-seat-model

Authority:
`.loom/tied/dashboard-8-identity-sim-design/` (proposal.md +
ratification.md + two surveys with file:line for everything touched).

The seats/devices split in dashboard state. Work before d8-2/d8-3.

- [x] **Schema**: `installation.json` gains `seats` (keyed by id-as-string:
      `{id, name, positions: [[x,y]…] (true-N ready), patch, params,
      bound: <uid>|null}`) — all piece data moves off device rows. Device
      roster keeps identity/runtime only: uid, hostname, last_seen, ip,
      version, engine_alive, rssi, report, rev, sync, plus
      `virtual: true` for sim rows (never persisted). Rework
      `dashboard/state.py` (`DURABLE`, `_runtime_device`, `durable()`).
- [x] **Hard break — no migration** (Bob §7 ruling): the new shape replaces
      the old; old `installation.json`/venue files are not honoured. Add a
      `schema` version field so *future* changes can migrate.
- [x] **ws surface**: seat CRUD (`add_seat`, `update_seat` — name/positions/
      patch/params, `remove_seat`), `bind_seat {id, uid}` / `unbind_seat
      {id}` (bind fires the existing `OSCBridge.assign()` with seat data —
      wire untouched), `forget_device {uid}` (unbind first; confirm-gated
      client-side only when recently seen, Q4) and `forget_offline_unbound`
      (bulk). Replace `assign_device`/`set_position` handlers
      (`server.py:209-227,279-305`) with the seat equivalents.
- [x] **Venue save/load** carries seats (incl. `bound` uid memory);
      auto-rebind on load: a remembered uid that is currently heartbeating
      rebinds automatically (Q5), others load unbound.
- [x] **Heartbeat path**: `ensure(uid)` still creates roster rows for any
      `/hb`, but rows carry no piece data; the assign-replay logic in
      `osc_bridge.py:264-288` now reads from the bound seat.
- [x] verify_*.py (Playwright or ws-level): seat authored before any device
      exists, bind pushes /os/assign with seat data, unbind/rebind (device
      swap), forget + bulk forget, venue round-trip with auto-rebind.

Coordination: hostname-in-`/os/report` (Q6) lands node-side via
`dist-1`/`dist-2` (patch-asset-sync) — this stitch only consumes the field
if present.
