# 6b-show-management worklog

2026-07-19, autopilot session.

## What was already there

The backend surface for this stitch existed in full before work started
(stitches 2 and 6 plus the empty-state form from stitch 4): `create_show`,
`load_show` (stops playback first), `save_show_as`, `delete_show`,
`list_shows`, `current_show` persisted in the installation state and
broadcast on the `shows` WS message. The gap was entirely operator-facing:
once a show was loaded there was no way to reach any of it, and there was
no rename.

## What this stitch added

- `server.py`: one `rename_show` handler — same name sanitation as
  `create_show` (word chars and dashes, 48 max), refuses collisions, saves
  the loaded doc under the new name, deletes the old file, adopts via
  `set_current_show`. Renaming does not stop playback (item uids are
  unchanged, so engine state stays valid).
- `show.js`: a `.show-manage` cluster in the transport strip — saved-shows
  select plus Load / New / Rename / Delete. Dialog idioms match the rest of
  the dashboard (`prompt` for names, `confirm` for destruction). Switching
  confirms only when something is playing or paused; loading the
  already-current show is a no-op. Delete acts on the *selected* show in
  the dropdown (so non-active shows can be deleted); deleting the active
  show falls back to the empty state, which already offers create/load.
- `style.css`: compact 30 px controls in the strip with the `::after`
  expanded-hit-area trick (`.show-icon-button` precedent) so touch targets
  stay ≥ 40 px without spending header height; the ≤ 760 px layout restores
  full-width 44 px controls.
- `dashboard/README.md`: one paragraph noting the catalog controls.

Deferred (allowed by the instructions): a duplicate/"save as" button. The
`save_show_as` WS handler exists and works — only the button is missing;
add it to the same cluster if wanted.

## Layout regression caught and fixed

The first cut used 44 px controls in the strip; at the 5b dense-layout
budget (768×1024, 20 steps + divider) the cluster wrapped and pushed the
table 23 px past the viewport, failing tied 5b's
"fit unscrolled" check. The compact-control restyle above brought it back
under budget with no change to 5b's assertions.

## Verification

`verify_show_management.py` (this dir, house pattern: real server +
simfleet + headless Chromium): create-becomes-active, new show empty with
add affordance, switch both ways with content intact, switch-while-playing
stops the transport, rename keeps content and drops the old name, delete
removes from the catalog, second-client convergence, active show survives
a server restart (past the 1 s debounced state save), no page errors —
11/11 pass.

Full tied-verify sweep after the change, all green: 2-model,
3-playback-engine, 4-tab-ui, 5-inspector, 5b-compact-rows,
5c-target-model-and-picker, 6-message-editing, 7-osc-consoles. No tied
assertions needed amending.
