# Results — Seat-group UI revisions

## Outcome

- Replaced the combined Seats sidebar with peer local **Seats** and **Groups**
  tabs while keeping Venue outside both panels.
- Removed group-catalog search, Seat-detail group search, the listener heading
  readout, and duplicate sidebar Simulation status.
- Kept a single selected-group **Filter Seats** field. It matches Seat display
  names by case-insensitive prefix, responds to typing and Enter, and retains
  its value, focus, and caret across live dashboard rerenders.
- Preserved group membership editing, visibility controls, map overlays, and
  the stable four-slot rail layout.

## Verification

- Focused real-browser verifier: **17/17 passed**
  (`verify_seat_groups_ui_revisions.py`). This includes actual row visibility,
  typing, Enter, empty results, rerender survival, keyboard tabs, membership
  mutation, map selection, overlays, and browser page errors.
- Existing Seats workspace browser regression: **12/12 passed**.
- Dashboard group-state/core suite: **6/6 passed**.
- `node --check` passed for `dashboard.js` and `spatial.js`.
- Verifier compilation and `git diff --check` passed.
- Visually inspected `seat-group-tabs.png`: the Groups panel hierarchy is
  clear and `front` displays only `Front 1`, `Front 2`, and `FRONT 3`.

## Unexercised surfaces

The physical iPad, installation projector, LAN/node, audio engine, and audible
rig were not exercised. No `.pd` file changed.
