# 4-sites verification — 2026-10-04

Implemented site geometry storage in `dashboard/state.py`, its server handlers,
OSC assignment/reappearance paths and CSV export. `project.json` holds
`current_site`; each `sites/<name>.json` holds only room, listener and positions
keyed by Seat id. Stored Seats carry no geometry. The public Seat positions
are a derived view of the current site for existing map and inspector clients.

Switching flushes the outgoing site's pending edits, saves the pointer and
new geometry, and replays assignments, groups and the audition listener through
existing paths. Project identity, bindings, groups, parameters, Wi-Fi and Show
selection remain project state. Seat reindex/delete update every site's map;
failed writes restore the previous files and geometry.

Removed venue save/load/read/list APIs, their WebSocket snapshots and rebinding
UI, the venue bar and its dead CSS. A minimal Site selector sits on Seats;
dashboard Site and Remote title read the current site. No New Site dialog or
project menu was added. Header markup, header CSS and project-bar.css were not
edited; only the retired venue rules were removed from shared style.css.

Migration tools:

- Legacy installation: `python tools/migrate_project.py dashboard/installation.json`.
- Existing project-storage layout:
  `python tools/migrate_sites.py dashboard/projects/<project>/project.json`.
- Both produce default geometry and convert snapshots from the legacy
  installations directory only when Seat ids match. Non-matches and name
  collisions are reported and preserved. All legacy sources stay untouched;
  the site migration saves original project bytes as `project.json.pre-sites`.
  Existing destinations are refused. Runtime loading has no legacy fallback.
- Migrations were verified against isolated fixtures; local operator data was
  not converted during implementation. The old installations ignore rule
  remains to keep preserved legacy sources out of git; runtime has no path to it.

Verification:

- `./tools/run-tests.sh fast`: 408 tests PASS.
- `python tests/test_sites.py` with project venv: 9 tests PASS.
- `./tools/run-tests.sh browser`: all 24 journeys PASS.
- New `tests/verify_sites.py` covers real Site selection, room/listener/position
  changes, independent geometry, immediate-switch edit flushing, reload,
  exact physical OSC assignment and group replay, CSV export and Remote title.
- Updated compact project fixtures and retained all non-venue journeys.
  Removed four obsolete venue unit tests; site safety/migration coverage added.
- JavaScript syntax and `git diff --check` PASS.

No OSC wire changes. `docs/OSC-CONTRACT.md` was left untouched (its old
`installation.json` reference remains at line 859). No commits or loom
lifecycle commands. Unrelated concurrent work and protected files were left
untouched.

## Review revision r2

Group resolution warnings, group-uniqueness errors and the group-name adoption
notice now say project. Updated related Show model and Remote-command comments
and docstrings; Remote's page-furniture comment says site name, matching its
current-site title. Updated the Show targets journey's old venue-id check label.
No tests asserted the retired message text.

Requested verification: fast suite 408 PASS; `verify_sites.py` PASS;
`verify_show_targets.py` PASS. JavaScript syntax and `git diff --check` PASS.
