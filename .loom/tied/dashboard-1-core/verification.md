# dashboard-1-core — verification (2026-07-08)

Verified against simfleet on loopback and in a real (headless Chromium)
browser. **Not verified against a real fleet** — see the end.

## Integration suite

`test_dashboard.py` (this dir) — 11 checks, all passing. Boots server.py +
simfleet on high ports, drives the WebSocket:

```
<dashvenv>/bin/python .loom/tied/dashboard-1-core/test_dashboard.py
```

Covers: WS connect + initial full state; 3 sim devices discovered by uid
from v1 /hb (2 assigned + 1 unassigned); params_declaration from the
default-patch manifest; report with contract_version 1.0; set_param
reaching the sim (legacy bare form observed on the wire) and persisting to
installation.json after the debounce; aloha action; master mute; and the
undeclared path driven directly (empty /os/params reply → legacy four +
badge — simfleet can't produce it, it always has a manifest).

The dev venv (fastapi, uvicorn, python-osc, websockets, playwright +
chromium-headless-shell) lives at `<session-scratchpad>/dashvenv`; recreate
with `python3 -m venv … && pip install -r dashboard/requirements.txt
playwright && playwright install chromium` (pip exists on this box).

## Browser drive — headless Chromium via Playwright

`verify_dashboard.py` (this dir; written by codex, whose sandbox couldn't
launch Chromium — run by the orchestrator instead). Stack: server on real
ports, `simfleet --devices 5 --unassigned 1 --engine-dead 1 --wired 2
--target 127.0.0.1`, seed csv naming sim1–4. All 7 steps pass, **zero
console/page errors** (`results.json`):

1. Overview: 5/5 online, 4 assigned rows + 1 unassigned (labeled by uid —
   /hb carries no name; names come from seed/assignment). `01-overview.png`
2. Detail: uid/id facts, params rendered from the manifest (gain/backing
   sliders, echo checkbox, MIX/FX groups), no UNDECLARED badge, full
   actions row. `02-detail.png`
3. Report panel fills: engine pd, contract_version 1.0, humanized uptime.
4. Slider drag → value survives page reload (server-side persistence).
5. MUTE ALL → loud "MUTED — UNMUTE" state (and back off after).
6. Engine-dead device's dot is amber ("crashed") vs green online — the
   box-up-engine-dead distinction from contract §6, visible at a glance.
7. No JS errors across all of the above.

### Bug found by the browser pass (fixed)

The final slider value could be lost on release: the document-level
pointerup re-render detached the input before its `change` event fired, so
the last send could carry a stale intermediate value (UI showed 0.29,
server persisted 0.24). Fixed in dashboard.js: send on the input's own
target-phase `pointerup` + optimistic local state update; duplicate sends
are safe by the contract's idempotent full-state law. Re-run: drag 0.24 →
reload 0.24.

## Not verified (needs a real network / Bob)

- Real fleet: UDP **broadcast** send (loopback used unicast target);
  coexistence with DASHBOARD.pd on 5550 (SO_REUSEPORT is set, untested with
  PD listening); real Pi heartbeats.
- iPad/tablet: layout is responsive by construction, not tested on device.
- The stitch's done-bar ("real installation mixed from a browser") needs
  the above — flagged, not claimed.
