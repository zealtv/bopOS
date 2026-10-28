# 3-asset-send-queue

The server-side queue that sends an asset slot to devices one at a time.

## Behaviour (Bob, 2026-10-28: option B, one-off, one at a time)

- Jobs are *(device uid, slot)*. `send_distribution` with `kind: "asset"`
  accepts `uid: "all"` (every online, assigned, physical device) or one
  uid, and appends jobs. A send while the queue runs just appends. The
  current single-device Send and Update go through this queue too, so there
  is one path.
- Jobs run one at a time. When a job's turn comes:
  - **skip** it if the device is offline, unassigned or virtual, or if its
    inventory fingerprint for the slot already matches the host's;
  - otherwise reset `ServedBytes` (`2-`) for the device's IP, call
    `osc.fetch(...)` (unicast after `1-`), and follow the device's
    `fetch[slot]` phase.
- **done** on `/os/fetched ok`; **failed** on `err` or `timeout`, if the
  device goes offline, or if there's a stall: no served bytes and no
  manifest hit for `FETCH_STALL_SECONDS` (120 s) after the phase reaches
  `fetching`. Allow for the Pi's hashing pass before downloading (about
  20–25 s per GB, per `.lore/items/2026-07-15-asset-transfer-scale-reference/`),
  so measure the stall from the last activity, not from the start. After a
  failure the queue moves on. A late `/os/fetched ok` for a failed job turns
  it to done.
- Each job carries `bytes_sent`, refreshed about once a second from
  `ServedBytes`. It also carries `bytes_total` when the slot was absent on
  the device (total = the slot's catalog bytes, so the percentage is exact);
  otherwise `bytes_total` is null (an update, where the Pi skips unchanged
  files).
- **Cancel remaining** removes waiting jobs; the running job finishes,
  because the contract can't cancel a transfer on the node. **Retry** adds a
  failed job back to the end. **Dismiss** clears a finished queue.
- After each done job, re-query that device's asset inventory, as single
  sends do now.
- A dashboard restart loses the queue. Rows fall back to the observed
  inventory. Write this in the UI copy (`4-`), not just here.
- The active-slot warning is confirmed once per send. The server refuses an
  unconfirmed send when any target's active patch declares the slot (the
  same rule as today, extended to All).

## Wire to the browser

A new websocket snapshot type `asset_queue`: `{jobs: [{uid, slot, state,
bytes_sent, bytes_total, error}], running, finished}`. List it in
`dashboard/static/js/ws.js` `SNAPSHOT_TYPES` (glean `ws-snapshot-handlers`)
and include it in the public state snapshot. The new websocket messages
are `cancel_asset_queue`, `retry_asset_job` and `dismiss_asset_queue`.
`single_asset_target` relaxes to "each job's device must be eligible when
its turn comes".

Remove stays single-device and immediate. "Remove from All" waits until Bob
asks for it.

## Verify

Unit tests with a fake bridge: one job runs at a time; skips (current,
offline); done/failed/stall; a late ok after a failure; cancel; retry;
`bytes_total` only for absent slots. Then a simfleet run: three peers
fetching a real slot one after another.
