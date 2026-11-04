# 28-ws-self-close

**Arrived:** 2026-11-04, nest item `for bob.rtf`: terminal output from another
Mac running the dashboard (`other-mac-log.txt`, kept here). Bob: "errors
popping up in the dash"; they had tried to update bopOS on Theo River and the
errors "might have been prior to that".

## What the log shows

Each browser socket logs `accepted`, `connection open`, `connection closed`,
then `RuntimeError: WebSocket is not connected. Need to call "accept" first.`
from `receive_json` (`dashboard/server.py` ~361). That Mac ran Python 3.9 in
`~/.venvs/bopos`.

## Reproduced here (2026-11-04)

The same `RuntimeError` appears when the Monitor transport's writer closes
the socket itself (code 1013). `monitor_transport.py` `send_core()` sets
`closed` when the queue overflows: a snapshot over `SNAPSHOT_BYTES` (4 MB),
more than 256 rows queued, or too many bytes queued. `write()` also closes on
a send error or a 2 s send timeout. Once starlette has sent a close, the next
`receive_json()` raises `RuntimeError`, not `WebSocketDisconnect`, and the
read loop doesn't catch it. Reproduced by forcing `SNAPSHOT_BYTES = 100`;
the repro script is in the session scratchpad, not the repo. The `finally`
cleanup still runs, so the traceback itself is noise. The 1013 close is what
matters, because the browser reconnects and gets cut off again.

**Not known:** which limit that Mac hit. My guess is an oversized `state` or
`distribution` snapshot, because the cut-off happens on every connect, but
that guess is unverified. A slow browser or the 2 s timeout fit the log too.

## To do

1. Find out from that Mac, or by logging, which limit closed the socket. The
   writer swallows the reason silently; log one line naming it (overflow kind
   and size, or the send error).
2. End the read loop quietly once the transport has closed the socket. Treat
   it like `WebSocketDisconnect`, not an ASGI error.
3. If a snapshot really exceeds 4 MB on a real project, decide between
   shrinking it and raising the limit. Ask Bob before changing limits.
4. Test: a socket closed by the writer leaves no ASGI error, and the reason
   is logged.
