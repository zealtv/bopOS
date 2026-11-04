# Verification (2026-11-04)

- Bob's Mac: `./tools/run-tests.sh fast`, 661 OK, including the new
  default-port test. `verify_ws_snapshot_replay.py` and `verify_osc_tab.py`
  pass.
- Rachel's Mac (`rachellewindon@192.168.0.101`, over Bob's ssh session):
  pulled to `6a552e8` and started `nohup ./run.sh > ~/bopos-dashboard.log
  2>&1 &`. The banner reads `Dashboard on http://192.168.0.101:5580/`. A
  local client that sends the page's first message stays connected 5 s via
  `ws://localhost:5580/ws` (15 messages) and `ws://192.168.0.101:5580/ws`
  (7 messages). The same client on :8080 failed with 1002 earlier that day.
- Bob confirmed in chat that the dashboard works in her browser on 8081
  ("8081 works"). Her browser on 5580 not yet confirmed.
