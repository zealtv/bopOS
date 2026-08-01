# 03-osc-send-tab results

## Outcome

- Added a Monitor Send prompt with inferred OSC `i` / `f` / `s` types and
  explicit `i:` / `f:` / `s:` overrides.
- Quoted strings and session up/down history are supported.
- Moved the Show builder's typed-argument helper onto the shared
  `window.OscMessage` utility rather than creating a second client-side type
  grammar.
- Added a narrow, validated `monitor_send` WebSocket route. It sends only
  through the existing OSC bridge's active execution destination, so all sends
  use the established LAN/engine boundary and appear in Outgoing.
- Both client and server reject malformed addresses, invalid types, signed
  int32 overflow, and floats requiring more than six significant figures.

## Verification

```text
node --check dashboard/static/js/osc-message.js
node --check dashboard/static/js/monitor.js
node --check dashboard/static/js/show.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/test_monitor_send.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/20-console-dock/03-osc-send-tab.stitching/verify_monitor_send.py
git diff --check
```

Results: **4/4 living validation tests** and **7/7 real-server + simfleet
Playwright checks** passed. The known command was observed through simfleet's
reply, and Chromium reported no page errors.
