# dashboard-3-discovery-assign — verification

Date: 2026-07-08, dev laptop, loopback (real dashboard + real simfleet with a
node-side state dir, headless Chromium driving the UI).

## What ran

`verify_assign.py` — 11/11 PASS, the whole discovery→assignment story:
- unassigned nodes (heartbeating `id = -1`) appear in the pool automatically,
  keyed by uid; params/actions are hidden until a device is assigned
- assign form pre-fills the next free ID; Identify sends a **uid-targeted**
  `/all/os/identify <uid>` (an id selector would flash every -1 box at once) —
  simfleet logs the identify
- Assign pushes `/all/os/assign <uid> <id> <name>`; the node applies and
  **persists** it (simfleet's state dir gains `{id, name}`), and the device
  moves to the assigned list with a sanitised name
- dragging the newly-assigned device onto the map rides a follow-up
  `/os/assign` carrying positions — the node persists those too
- an ID collision is refused with an explanation, not silently applied
- `GET /bopos.devices` exports the live assignments as the seed/export CSV
  (no longer the source of truth — the dashboard's `installation.json` is)

Screenshots: `01-assign-form.png`, `02-assigned.png`. Sibling suites
(os-admin-verbs, spatial-map) re-run green after the server/bridge changes.

## Test-harness gotchas found (not product bugs)

- `inner_text` applies the row's `text-transform:capitalize`, so name
  assertions lowercase the result.
- Clicking the assign button auto-scrolls the page; the test scrolls back to
  the map before dragging. Real operators scroll too — a UX note, not a bug.

## Not covered (needs a real rig / Bob)

- A real Pi persisting `/os/assign` to `state/store` and surviving a reboot
  with the network down (standalone operation) — simfleet models persistence
  but isn't the real Store.
- Touch assign/drag on an iPad.
- Migrating an installation that still has a hand-maintained `bopos.devices`:
  the seed import path is unchanged, but a live cutover wasn't exercised.
