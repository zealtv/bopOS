# dashboard

**Goal:** the bopOS web dashboard becomes the primary interface for the whole system —
monitoring devices, controlling gain/patches, arranging devices spatially (top-down X/Y
map), managing patches, and updating the bopOS framework itself. Replaces DASHBOARD.pd.

Full design (stack, OSC bridge, WebSocket protocol, UI mockups, state file):
`.notes/dashboard-development-context.md`. Review context:
`.notes/architecture-review-2026-07-05.md` §8.

Stack decided: Python 3 + FastAPI + python-osc backend, vanilla HTML/JS/CSS frontend,
SVG spatial map, `installation.json` state file. No build step, no framework, no logins.

Children were delivered through the original phases and subsequent UI, identity,
distribution, fleet-patch, patch-editor, and workspace work.

---
**2026-07-15 closure:** Bob removed `dashboard-6-rig-adoption` as a separate
loom gate. Real-installation adoption and retirement of DASHBOARD.pd fall out of
ordinary development and use; they are not a discrete tracked deliverable. The
software dashboard work is complete. Quickstart: `dashboard/README.md`.

Constraints:
- Don't edit `.pd` files — PD is Bob's domain.
- (The phase-1 no-Pi-changes and heartbeat-identity constraints above are
  resolved history — identity landed, DASHBOARD.pd coexistence held.)

---
The later dashboard work and verification records remain in `.loom/tied/`.
Hardware, audible, and iPad observations in those records remain honest
boundaries; closing this tracking goal does not retroactively claim them.
