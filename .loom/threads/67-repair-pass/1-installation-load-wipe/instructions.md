# 1-installation-load-wipe

**Status:** ready · confirmed by reproduction
**Goal:** a state file the dashboard can't fully read is never overwritten, and
the operator is told.

## The bug

`InstallationState._load` (`dashboard/state.py`) is all-or-nothing: one seat
naming a missing group (or any field failing its cleaner) sets
`_load_invalid` and the dashboard starts empty, silently. `save()` doesn't
check `_load_invalid`, so the next ordinary save (master fader, a new device
alias) replaces the real file with an empty installation. Repro in `lore:2026-10-03-bopos-code-review-2026-10`.

## Fix (shape is yours)

- Never write over a file that failed to load. Keep the original (e.g. copy to
  `installation.json.invalid-<timestamp>`) before anything else happens.
- Tell the operator — the existing `notices` channel is the place.
- Consider repairing what's repairable (drop a dangling group reference with a
  notice) rather than discarding everything. Group-name adoption is the
  precedent. Ask Bob only if it changes what he'd see beyond a notice.
- Check venue loading (`read_venue` / `load_venue`) for the same shape.

## Done when

- Test: invalid file + a save → original bytes preserved, notice present.
- Test: dangling group reference → handled as decided above.
