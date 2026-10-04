# 7-project-menu — verified

Menu and New Site dialog match the ratified structure and wording; the minimal
Seats picker is removed. Current entries appear first and are highlighted.
All four WebSocket handlers are wired with the approved errors. New Project
creates no Seats, show file or patches. Rename moves the folder and updates
current-project, refusing collisions/invalid names and rolling back the move
if selection writing fails. Opening validates the candidate, stops Show playback,
loads project/site/show/patches, clears old automation and pending patch pushes,
replays assignments/groups/parameters, and sends exact-UID unassign to online
physical outsiders. Simulation/Patch Edit refuse project switching. Patch
delivery stays explicit. Host devices, registry and mute state stay host-global.
Project changes reset old browser authoring drafts.

User-approved name grammar is shared by state and migration tools: preserve
names as typed, including internal spaces; start with an ASCII letter or digit;
allow letters, digits, space, dot, underscore and hyphen; reject trailing spaces,
slashes and any double dot. Folder/file names remain the sole identity. Invalid
legacy names are refused/reported rather than automatically slugged.

Verification:

- `./tools/run-tests.sh fast`: 424 tests PASS.
- `./tools/run-tests.sh browser`: all 26 journeys PASS, including
  verify_project_menu, verify_sites, verify_show_targets and verify_patches_tab.
- Seven new unit tests cover empty creation, rename file preservation,
  invalid names/collisions, spaced identities, selection-write rollback,
  copied unflushed geometry, assignment replay, outsider unassign and mode guards.
- The real two-node simfleet journey covers menu dismissal, copied/empty sites,
  opening a second project, outsider unassign, rename, New Project, reload,
  unchanged registry, and no page errors or server error alerts.
- JavaScript syntax checks and `git diff --check` PASS.

Final screenshots regenerated via BOPOS_PROJECT_MENU_SCREENSHOT and
BOPOS_NEW_SITE_SCREENSHOT; both visually inspected in dark theme:

- `/private/tmp/claude-502/-Users-bob-repos-bopOS/eb6fbb68-c7f7-4a02-aeed-7744c61ade65/scratchpad/project-menu.png`
- `/private/tmp/claude-502/-Users-bob-repos-bopOS/eb6fbb68-c7f7-4a02-aeed-7744c61ade65/scratchpad/new-site.png`

Documentation updated. No OSC contract edits, Pure Data edits, commits or loom
state transitions performed by Codex. Claude's existing stitch move and the
untracked .codex/.obsidian directories were left alone.
