# dashboard

**Goal:** the bopOS web dashboard becomes the primary interface for the whole system —
monitoring devices, controlling gain/patches, arranging devices spatially (top-down X/Y
map), managing patches, and updating the bopOS framework itself. Replaces DASHBOARD.pd.

Full design (stack, OSC bridge, WebSocket protocol, UI mockups, state file):
`.notes/dashboard-development-context.md`. Review context:
`.notes/architecture-review-2026-07-05.md` §8.

Stack decided: Python 3 + FastAPI + python-osc backend, vanilla HTML/JS/CSS frontend,
SVG spatial map, `installation.json` state file. No build step, no framework, no logins.

Children are the four phases in order (1 → 4). Tie this goal when the PD dashboard is
retired and the web dashboard is the daily driver on a real installation.

Constraints:
- Phase 1 requires **no Pi-side changes** (coexists with DASHBOARD.pd during migration).
- Later phases coordinate with `osc-schema-contract` (heartbeat identity) — the dashboard
  gets much simpler once heartbeats carry MAC/ID, but must work without it first.
- Don't edit `.pd` files — PD is Bob's domain.
