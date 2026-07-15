# tabs-1 skeleton results

Implemented the ratified six-tab shell without changing the dashboard backend:

- **Dashboard** is the default live-control view, with master, cues and presets;
  the existing touch surface is embedded and `/facilitator` remains a renamed
  standalone compatibility entry.
- **Seats** owns the map, points, seat list, simulation and venue controls.
- **Devices** owns the active/recent roster, unbound roster, device detail,
  individual/bulk administration and fleet-patch convergence.
- **Patches** owns the complete landed patch editor.
- **Assets** and **Sequencer** are explicit placeholders.
- URL hashes preserve/deep-link the active tab; the tab list has ARIA roles and
  keyboard arrow/Home/End navigation.

The ratified admin-command amendment also landed using the existing `action`
wire: every venue-promoted verb renders once at fleet scope and within each
device card at single-device scope. Existing confirmation/hold guards apply to
both. Per-device disclosure state is retained across heartbeat re-renders.

## Verification

- `verify_tabs_skeleton.py`: **20/20 passed** against the real dashboard,
  two-node simfleet and headless Chromium. It checks tab order/default/hash and
  keyboard-ready ARIA state, every placement, Dashboard embedding, promoted
  params, both admin scopes, master/cue/room behavior, device inspection,
  placeholders, compatibility routing and browser errors.
- Visual review of `01-dashboard.png`, `02-seats.png`, `03-devices.png`, and
  `04-patches.png`: the mechanical layout is coherent at 1440×1000; whitespace,
  roster repetition and final touch density remain appropriate topics for
  tabs-2 rather than paper polish here.
- `node --check dashboard/static/js/{dashboard,facilitator,spatial}.js`: passed.
- `git diff --check`: passed.
- The tied ui-0..3 browser scripts reach the relocated DOM but fail their old
  assumption that Seats/Devices content is visible at bare `/`; those location
  assertions are superseded by the focused tabs verifier. The retained seam-4
  facilitator verifier also retains its pre-existing stale parameter setup
  failure. No behavior failure from these runs was observed.
- No `.pd` file or OSC contract was changed. Hardware, iPad/touch interaction
  and final UI judgment remain the explicit tabs-2 review boundary.
