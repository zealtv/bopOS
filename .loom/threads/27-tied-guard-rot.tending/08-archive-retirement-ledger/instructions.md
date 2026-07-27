# 08-archive-retirement-ledger

Close the historical archive without deleting its evidence.

- Collate the migration matrices and decisions from children `01`–`06`.
- Record each relevant tied guard or guard family as promoted, retired
  authoring evidence, superseded, environment/hardware-only, or still needing
  an explicitly named follow-up.
- Point promoted entries at their owning living `tests/` surface.
- Preserve `.loom/tied/` artifacts; do not repair them merely to make a sweep
  green and do not add `tools/guard-sweep.sh`.
- Remove stale workflow language that implies the tied archive is a regression
  suite, while retaining the interim supersession rule for guards encountered
  during unrelated work.

Tie the parent only when the living-suite workflow and retirement record are
complete and the archive has no ambiguous maintenance status.
