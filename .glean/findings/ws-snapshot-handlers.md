# Late websocket handlers only see snapshots listed in ws.js

When adding `ws.on(<type>, …)` in a script that loads after `dashboard.js`, check the type is in `SNAPSHOT_TYPES` in `ws.js`, or the handler can miss the connect burst forever.

There is no periodic full-`state` broadcast (heartbeats are `device_update`), so a missed `state` never recovers. `SNAPSHOT_TYPES` is pinned against the server's connect burst by `tests/test_ws_snapshot.py`. `broadcast()` recomputes `public_state()` for `state` itself and ignores the caller's payload.

Probe protocol shape: `{"type": …, "data": {"uid": …}}` — a top-level `uid` is silently ignored.

## Triggers

- SNAPSHOT_TYPES
- ws.on
- public_state
- device_update

## Associations

- [[dashboard-vocabulary]]
