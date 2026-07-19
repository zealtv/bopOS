# live-param-catchup — replay live params when a device appears

**Goal:** when a device pops up (first heartbeat, or heartbeat after an
offline period), it automatically catches up on the dashboard-owned live
parameter values without Bob pressing anything.

Bob, 2026-07-19: "when a device pops up - it should receive some sort of
'send all' message to automatically update its params ie a catch up."

## What already happens on appearance (osc_bridge.handle, `/hb` branch)

- **Assignment** replays when `not old["online"]` (rate-limited via
  `_assign_replayed` / `ASSIGN_REPLAY_MIN_SECONDS`).
- **Groups** replay only after the convergence gate — the first heartbeat
  whose advertised id matches the configured Seat id
  (`configured and not reassign and advertised_id == configured_id`).
- **Device mute** replays every heartbeat (additive UID verb).

What does **not** replay: promoted live-control values. Those live in
`seat["params"]` and are sent seat-addressed via
`self.osc.set_param(seat_id, identity, value)`. Today there is only the
manual `replay_live_params` WS action (server.py, per-Seat/All scopes).

## Recommended design (decided; implement unless it fights the code)

Piggyback on the **same convergence gate as groups**: a seat-addressed
param is only applied by a node that already routes as that Seat, so
sending params before the matching-id heartbeat is a race. In the branch
where `send_groups` is triggered, when the device transitions to
converged-after-appearance, replay that Seat's params using the existing
per-declaration loop from `replay_live_params` (factor it so server and
bridge share one helper; scope = the one seat). Rate-limit with the same
pattern as `_assign_replayed` so heartbeats cannot form a resend loop.

No contract change: this is dashboard-side retransmission of the existing
idempotent full-state `set_param` writes (last-writer-wins, wire
discipline unchanged). Do **not** bundle params into `/all/os/assign`.

Edge cases to honour:

- Only replay identities present in the staged host manifest's live
  declarations (`live_control_declarations()`), same filter as the manual
  action — durable stale keys in `seat["params"]` must not resurrect.
- Simulation/audition parity: virtual devices reach the same branch;
  keep behaviour consistent with the manual replay's targeting rules.
- Manual replay action stays (it covers "I changed the manifest" /
  paranoia cases); this stitch just automates the appearance edge.

## Verify

Headless simfleet verify (`verify_*.py`, house pattern): start a fleet,
set live params, kill/restore one device (simfleet `--unresponsive` or
restart), assert the reappearing device receives assignment → then params
after the matching-id heartbeat, and that steady-state heartbeats do not
re-send params.
