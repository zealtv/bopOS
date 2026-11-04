# Verification (2026-11-04, this Mac, Python 3.14, starlette 1.3.1)

## Change

- `dashboard/monitor_transport.py`: `Client.close_because()` logs one
  `WARNING` line on `bopos.dashboard` when the dashboard closes a browser
  connection itself. It names the browser address and the reason: which
  queue limit was hit (message type and size), a send that took over
  `SEND_TIMEOUT`, or a send error. A browser that leaves
  (`WebSocketDisconnect`) or a disposed connection logs nothing.
- `dashboard/server.py`: the read loop runs `while not ws.closed`. Once the
  transport has closed the socket, the loop ends quietly instead of calling
  `receive_json()` and getting starlette's `RuntimeError`. No await falls
  between the check and the call. A receive already waiting when the writer
  closes gets starlette's `WebSocketDisconnect`, which the loop already
  catches.
- No limits changed.

## Checks

- `tests/test_ws_self_close.py` (new) drives `Dashboard.websocket` with
  `SNAPSHOT_BYTES` forced to 10 bytes. The loop ends, the socket closes, the
  editor release and client cleanup run, and one warning names the snapshot.
  With the `server.py` change reverted, the test fails with the same
  `RuntimeError` as the other Mac's log.
- `tests/test_monitor_transport.py`: an oversized snapshot and a send timeout
  each log their reason. A browser that disconnects logs nothing.
- `tests/test_ws_snapshot.py`: the source slice now ends at
  `while not ws.closed:`.
- Real server repro (the scratchpad script, with `SNAPSHOT_BYTES = 100`): the
  browser got close code 1013 and the server printed
  `WARNING:bopos.dashboard:Closed the dashboard connection to 127.0.0.1:…: state snapshot is 6301 bytes, over 100`,
  with no traceback. Ran three times. With normal limits, a clean close, an
  abrupt TCP drop and a 6 s stalled reader logged nothing.
- `./tools/run-tests.sh fast`: 660 tests OK.
- `verify_ws_snapshot_replay.py` and `verify_monitor_transport.py` pass
  (Chromium).

## Not verified

- Python 3.9 and the other Mac's starlette and uvicorn versions. The code
  uses nothing newer than 3.9. The new tests use `assertNoLogs`, which needs
  3.10+, but only the repo's test machine runs them.
- Which limit that Mac hit. That is `29-ws-close-reason-check` (Bob).
