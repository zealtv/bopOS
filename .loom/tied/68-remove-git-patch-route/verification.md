# Verification — Git patch-route retirement

2026-10-03. Phase 2 implements Bob's approval in `ruling.md`, without widening
the amendment. All five fenced amendment blocks in `proposal.md` match the
contract verbatim: header, §4.2 engine admin, §7, §9 landing, and §15 row.
`python/osc_contract.py` is 1.19. Earlier revision rows are unchanged;
`10-engine-id-int` can extend the same 1.19 row after this stitch.

## Software behavior

Removed the node provisioning callbacks and engine patch-update action,
patch-selection Git pull, pull script, Git inventory flag and fetch refusals;
removed the corresponding dashboard handlers/skips, Pull latest action,
marker/source diagnostics and unused CSS; removed simulator routes and flags.
Updated the current guides and READMEs and refreshed Glean's contract guidance.

Existing clones are ordinary installed directories. Selection validates and
uses their installed bytes without a Git subprocess. Push uses the existing
staging/convergence/validation/backup replacement flow: removing the landing
guard enables it without adding a second installer or early metadata deletion.
The live copy and metadata remain present during validation; failures leave
or restore them. A `.git` file is removed locally and its external target is
neither followed nor removed. Obsolete bytes are pruned, host dot metadata is
excluded, and existing symlink/traversal checks remain enforced. Active-clone
transfers now use the ordinary stop/converge/restart sequence and receipt.
Matching-fingerprint transfer skips and dashboard confirmation gates remain.

Regression evidence:

- `tests/test_fetcher.py`: public-route clone conversion, live metadata still
  present at validation, host metadata exclusion, obsolete-file pruning,
  `.git` pointer-file conversion preserving the external repository, and
  fetch/validation/installation failures for both metadata forms preserving
  all original bytes. A simulated replacement failure exercises backup
  restoration. Temporary staging and backup directories are cleaned up.
  Existing unsafe-path checks remain; added clone metadata symlink rejection.
- `tests/test_node_fetch_dispatch.py`: actual active-clone fetch with engine
  stop before convergence and restart before terminal success; metadata
  disappears only after successful replacement.
- `tests/test_admin_outcomes.py`: exact surviving node allowlists, selecting
  an installed clone without Git, and current node/dashboard inventory shape.
- `tests/test_simfleet_fetch.py`: current simulator inventory and engine admin
  allowlist. Existing simulator transfer serialization checks remain green.
- `tests/verify_device_control_modes.py`: ordinary four-column diagnostics
  without Pull latest, Git marker/source descriptions; full browser tier also
  exercises patch selection, hand-off and per-device/fleet convergence.

## Checks

- `./tools/run-tests.sh all`: **388 fast tests and all 23 browser journeys
  passed**, exit 0 (`tests.log`).
- Focused fetcher / node-fetch / admin / simfleet suites: 13 / 5 / 8 / 3 passed.
- Pyflakes on `dashboard/`, `python/`, `tools/` and changed regression modules:
  clean; Python compileall and dashboard JavaScript syntax check passed.
- `git diff --check`: passed.
- The stitch's exact retired-identifier `git grep` has no current executable
  or guide matches. Its remaining matches are Loom/Lore historical records,
  the §15 retirement row, and the explicit §7 removal statement required by
  the approved proposal (rather than a surviving route); see `retirement-grep.log`.
  Broader searches found no remaining Git deployment modes or UI outside
  retirement evidence and negative regression checks.

Framework update, checkout, convergence and revision reporting remain.
`python/io/sys_info.py` and `python/runcontext.py` resolve Git revision from
the framework root and are unchanged, as is `docs/PORTS.md`. No `.pd` files
were edited and no devices were contacted; no hardware result is claimed.
