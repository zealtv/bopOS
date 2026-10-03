# Verification — 2026-10-03

Removed host storage/application, all preset WS verbs and projections,
Control/Device/editor menus and Show PRE references, CSS and current usage docs.
Contract §8.1 is retired with §15 entry and shared version 1.18.
The parameter-schema hash has no remaining consumer and is removed.

Shared scalar canonicalization, automation estimates, replay and generator
takeover helpers moved unchanged into `dashboard/live_params.py`. Replay's
`effective_patch_for_seat` **is shared**, contrary to the inventory's tentative
classification; a retained replay test caught its removal, and it is retained.
Editor targets and ordinary Show target/group/UID/undo/transport behavior remain.

## Checks

- Final `tools/run-tests.sh fast`: **343 tests passed**. Feature-only tests
  were retired; shared automation coverage moved to `test_live_params.py`.
  Literal playback ordering, unsupported-kind rejection, HTTP file visibility,
  nested content hashing/fetch/prune and legacy unknown-field handling pass.
- Full `tools/run-tests.sh browser`: **23/23 journeys passed**. Removed the
  two obsolete feature journeys; retained mixed Control/Device/generator focus
  tests and renamed the Show reference journey to `verify_show_targets.py`.
- After deleting the unused asynchronous expansion hook, the focused Show
  target/copy/paste/undo journey passed again. No browser errors.
- Sandbox denied local sockets/Chromium; the actual browser pass ran outside
  that sandbox with authorized access. This is software verification, not a
  hardware or audio claim.
- Refreshed `docs/images/tab-dashboard.png` and `tab-dashboard-seats.png`
  using `capture_controls.py` with temporary state, patches and a two-node
  simfleet. Visually reviewed both: ordinary controls and no retired shelf.
- Current dashboard/Python/tools/tests/docs search for `preset` finds only
  contract §15 history. No Pd file was edited. Whitespace check passed.

Complete fast/browser logs and the focused Show log accompany this record.

## Authorized local cleanup

Bob authorized a clean break: no actual Shows need preservation, and obsolete
data should be gone with the feature.

- Removed the two PRE-only steps (`86668499`, `8c3264c3`) from the saved test
  Show. Preserved other working-tree edits; stage only the same removal against
  HEAD so unrelated literal cues/play-count changes remain unstaged.
- Removed the empty obsolete key from local ignored
  `dashboard/installations/10x8-test.json`.
- Deleted local ignored `patches/bonks-pd/presets/medium-bonks.json`, `off.json`,
  `sparse.json` and their empty directory. No tracked patch preset files existed.
  This local deletion cannot be represented in Git; it was performed and checked.
- Removed distribution host-only exemption. Ordinary prune-to-manifest now
  cleans stale nested files; no remote node was contacted or claimed cleaned.

No compatibility loader, migration service or replacement store was added.
