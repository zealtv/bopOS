READY FOR REVIEW

Implemented in 4554def; merged main before final verification (5d69d52).
No loom lifecycle state changed. No Pd files, node code, manifests or
osc_bridge code changed. No servers left running by this worker's journeys.

What changed

- `dashboard/state.py`: reusable `InstallationState.valid_group_name(name)`
  validates the ratified OSC target grammar without coercion; create/rename
  reject invalid names using one authoritative error. `convert_group_name`
  converts legacy text, and `adopt_group_names` resolves collisions with the
  existing load/save and session-notice mechanism. Suffixes respect 32 chars.
- `dashboard/static/js/dashboard-seats.js`: create/rename prompts state the
  character/length rule. Invalid or duplicate names show feedback in the
  existing group status strip, without sending a mutation. Server validation
  remains authoritative.
- `tests/test_show_model.py`: grammar/rejection tests for create and rename,
  migration tests for every reserved target, Unicode/punctuation, truncation,
  suffix collisions, legal-name priority, uniqueness and idempotence; existing
  adoption/reload tests updated for lowercase names and the notice.
- `tests/test_state_load_safety.py`: valid fixture uses `front`, preserving
  the test's no-notice expectation for a valid project.
- `tests/verify_group_names.py`: new real-dashboard Chromium journey, on
  private HTTP/UDP ports; checks invalid create/rename feedback, duplicates,
  successful edits, persistence and rejection of an editor-bypassing request.
- Browser fixtures in `verify_control_column_scroll.py`,
  `verify_control_surface_component.py`, `verify_control_tab.py`,
  `verify_event_control_panel.py`, `verify_ground_and_card.py` and
  `verify_show_targets.py` now use `front` (including selector expectations).
- `final-fast.log` and `final-browser.log`: complete post-merge test output.

Decisions

- Fresh edits must match exactly: no trimming, lowercasing or silent truncation.
  This makes editor feedback and the server's rejection consistent.
- Legacy names retain the previous surrounding-whitespace trimming, then
  lowercase; each remaining non-ASCII-grammar character becomes `_`, and the
  base truncates to 32 characters. Blank names use `group-<id>`.
- Reserved legacy names get `group-`: `all` -> `group-all`, `123` ->
  `group-123`, `g12` -> `group-g12`; plane names follow the same rule.
- Existing legal names have priority over converted names. Generated suffixes
  avoid every converted base, so `Front`, `front`, `front-2` become
  `front-3`, `front`, `front-2`. Remaining ties resolve in numeric group-ID
  order with `-2`, `-3`, etc., shortening the base as necessary.
- Contract inspection found numeric group selectors in §3, but no group-name
  grammar. No contract change made; the later input stitch owns that addition.

Verification

Commands use `~/.venvs/bopos/bin/python` through the repository runner.
After `git merge main`:

    ./tools/run-tests.sh fast
    Ran 623 tests in 39.831s
    OK

    ./tools/run-tests.sh browser
    38 PASS entries in the browser summary; exit 0.
    Tail:
    PASS verify_show_targets.py
    PASS verify_sites.py
    PASS verify_spatial_cancel.py
    PASS verify_state_load_safety.py
    PASS verify_target_picker.py
    PASS verify_value_box_component.py
    PASS verify_wifi_networks.py
    PASS verify_ws_snapshot_replay.py

Also passed: focused `test_show_model.py` (27 tests), the focused browser
journey, Python compilation of every changed Python file, Node syntax check
of `dashboard-seats.js`, and `git diff --check`. The implementation and merge
commits each passed the mandatory fast-test hook (623 tests).

An initial sandboxed fast run failed three manifest-boot tests because local
socket operations were denied. It was rerun outside the sandbox and passed;
final logs are from approved, unrestricted local test runs.

Review hardest

- The migration's legal-name priority and deterministic reserved-name prefix.
- Saved Shows are not rewritten by group-name adoption, matching the existing
  adoption/rename path. A Show containing `group:Front` needs retargeting after
  `Front` becomes `front`; the normal missing-group warnings expose stale
  targets, and the adoption notice lists old/new names. No name compatibility
  alias was added.
- Software/browser/simfleet verification only: no hardware, audio or iPad claim.
  No Pd edit is needed for this stitch.
