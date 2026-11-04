# 29-ws-close-reason-check

**Status:** Bob's: it needs the other Mac (the one in `28-ws-self-close`).
**Goal:** learn which limit made that Mac's dashboard close its browser
connections, then decide whether to shrink a message or raise a limit.

1. Update bopOS on that Mac to include `28-ws-self-close` (2026-11-04), then
   restart the dashboard and open it in the browser.
2. If the dashboard keeps reconnecting, the terminal now prints one line per
   cut-off, instead of the traceback:
   `WARNING:bopos.dashboard:Closed the dashboard connection to <ip:port>: <reason>`.
   Paste that line, or drop the terminal output in the nest.
3. With the reason in hand, an agent proposes a fix. For example, an
   oversized `state` or `distribution` snapshot gets trimmed. Changing the
   limits (`SNAPSHOT_BYTES` 4 MB, `CORE_ROWS` 256, `SEND_TIMEOUT` 2 s in
   `dashboard/monitor_transport.py`) is Bob's call.

If no warning appears and the dashboard behaves, the errors may have come
from that Mac's older checkout. Record that and tie this stitch.
