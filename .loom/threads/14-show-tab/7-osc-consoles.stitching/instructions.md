# 7-osc-consoles

Two live OSC consoles on the Show tab: outgoing and incoming. Requires
stitch 4 (tab exists); useful during 5–6 so earlier is fine if unblocked.

Scope:

- Backend taps: outgoing = everything the dashboard sends to the fleet
  (all tabs, not just the show engine); incoming = everything received on
  the LAN surface (heartbeats included — filtering makes this usable).
  Stream over WS with timestamps, address, args, and target/source;
  bounded ring buffer (drop oldest), rate-tolerant.
- UI: two console panels on the Show tab (collapsible; don't crowd the
  table), newest-last with auto-scroll that pauses when the user scrolls
  up, pause/clear controls.
- Filter box per console: substring match with `*` wildcards and `!`
  prefix for negation; multiple space-separated terms AND together
  (e.g. `/p/* !/sync`). Applied live, case-insensitive; filtering is
  client-side over the buffer.
- Keep the hot path cheap: no per-message DOM churn beyond the visible
  buffer; heartbeat floods must not degrade the tab.

Verify: `verify_show_consoles.py`, Playwright against simfleet. Cover:
outgoing console shows a triggered step's messages; incoming console shows
simfleet traffic; wildcard filter narrows correctly; `!` negation excludes
(e.g. hide /sync noise); pause and clear work.
