# 2-remove-presets

**Status:** after `1-preset-inventory`
**Goal:** carry out `1`'s plan.

Follow `../1-preset-inventory.tied/plan.md` and its `surface-audit.md`.
This is one coordinated removal: partial source/UI/test retirement cannot
independently meet the green-tier gate. Do not claim until the inventory's
operator-visible data decisions are settled.

## Checklist

- Extract shared live parameter canonicalization, replay and automation
  estimation into `dashboard/live_params.py`; retain their test coverage.
- Delete preset storage/application, server APIs and WS messages, catalogs,
  runtime provenance and Show reference/flatten machinery. Preserve editor
  automation targets, literal Show editing/transport and group warnings.
- Remove browser menus/drawers/reports/builders and their CSS/HTML links.
  Preserve input/focus guards and visible patch identity in Device controls.
- Implement the inventory's agreed stale Show and patch-file handling.
  Keep installation/venue unknown-field handling generic. Never rewrite or
  stage Bob's pre-existing `dashboard/shows/test.json` edits or delete authored
  local patch data.
- Remove the special distribution policy, retaining generic containment,
  hash, dotfile, symlink and partial-file safeguards.
- Apply the proposed §8.1 retirement and §15 amendment, synchronizing contract
  heading and shared report constant to 1.18. Revise current docs, affected
  screenshots and stale glean guidance; preserve historical records.
- Retire feature-only suites and rewrite mixed tests around surviving controls,
  automation, Show editing and distribution. Preserve generator focus checks
  and meaningful legacy-input rejection/byte-preservation coverage.
- Audit residual source/docs/CSS/WS identifiers and record fast + browser green
  evidence in this stitch before tying and committing.

## Done when

- No preset feature code, UI, CSS or current usage docs remain. Residual names
  are limited to history (contract §15, lore, tied/dropped loom records) and
  isolated stale-input fixtures that prove retirement handling.
- Contract §8.1 retired with a §15 entry.
- Supported saved shows and installations load cleanly; unsupported Show
  messages follow the agreed inventory decision without silent cue loss.
- `tools/run-tests.sh fast` + `browser` green.
