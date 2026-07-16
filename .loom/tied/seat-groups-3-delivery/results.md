# Seat-group delivery verification

Date: 2026-07-16

## Focused real-browser delivery pass

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/seat-groups/seat-groups-3-delivery.stitching/\
verify_seat_groups_delivery.py
```

Result: **20/20 checks passed**, with no browser page errors.

Coverage includes:

- ratified subordinate placement after Seat detail and before Simulation/Venue;
- collapsed visibility/catalog summary;
- state-oriented eye/eye-off iconography and accessible action labels;
- focus, compare, legend, clear, empty-group, and two-stage Escape behavior;
- four separate, numbered, patterned rail slots with stable slot retention;
- explicit rejection of a fifth visible group without replacing context;
- preserved canonical name plus `g<id>` identity;
- Seat-side and Group-side searchable membership checklists;
- create, rename, and delete behavior through the real WebSocket/backend API;
- dense 100-Seat rendering, a measured 44px-or-larger invisible Seat hit target,
  and rail contrast greater than 3:1 against the room background;
- 768px touch/mobile stacking, 44px eye controls, and touch visibility toggle.

The retained screenshot `seat-groups-delivery.png` was visually inspected. It
shows distinct rails outside unchanged element-index fills, the operational
Seat outline above the rails, canonical legend text, and subordinate sidebar
placement. The 100-Seat fixture deliberately produces a very long full-page
screenshot; it is scale evidence rather than a marketing mockup.

## Focused core and adjacent regression evidence

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/2-dashboard-state-sync/verify_group_dashboard_state.py
```

Result: **6/6 passed**.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/07-seats-workspace/verify_seats_workspace_browser.py
```

Result: **12/12 passed**, with no browser page errors. The two screenshots this
retained verifier regenerates were restored after the run.

Two older adjacent verifiers stop on pre-existing stale fixtures rather than
delivery assertions:

- `preview-3-dashboard-listener-puck` passes its first two checks, then expects
  a persisted invalid-room listener to clamp to the old room edge. Current
  state correctly restores the default listener at the fallback-room centre;
  the failure occurs before browser/spatial UI work.
- `tabs-1-skeleton` passes its tab order/default-view checks, then expects
  facilitator cards for simulator devices without any Seats. The authoritative
  Seats model now revokes those stale assignments, so that old empty-Seat
  fixture cannot produce promoted cards.

Neither stale verifier was edited in this stitch.

## Static checks

```sh
node --check dashboard/static/js/dashboard.js
node --check dashboard/static/js/spatial.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  .loom/threads/seat-groups/seat-groups-3-delivery.stitching/\
verify_seat_groups_delivery.py
git diff --check
```

Result: passed. No `.pd` file changed.

## Boundaries

- Browser touch emulation was exercised, but no physical iPad was used.
- No installation projector, physical node, LAN broadcast, audio engine, or
  audible rig verification was run.
- Promoted All/Group/Seat live controls remain intentionally absent; the
  downstream `12-dashboard-live-controls` stitch owns that matrix.
