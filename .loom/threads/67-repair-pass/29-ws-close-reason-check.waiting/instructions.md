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

## Observed 2026-11-04 (agent, over Bob's ssh session)

- That Mac (`rachellewindon@192.168.0.101`, Rachels-MacBook-Pro-3) was at
  `e5985af` with a clean tree and no dashboard running. Pulled to `995ce11`
  and started `nohup ./run.sh > ~/bopos-dashboard.log 2>&1 &` (pid 5500),
  serving http://192.168.0.101:8080/.
- A browser-style client from Bob's Mac received `state` (9640 bytes),
  `distribution` (1199), `show`, `show_warnings`, `show_playback`, about 20
  `patches` messages (~2.8 KB each) and `telemetry`. It stayed connected
  through 4 s idle. The log showed no warning.
- So in this state, every snapshot is far below 4 MB: the oversized-snapshot
  guess in `28` doesn't hold here. Watch the log
  (`grep -v '^INFO' ~/bopos-dashboard.log`) while the errors' conditions are
  recreated, such as a real browser, nodes online, or the Theo River update.
