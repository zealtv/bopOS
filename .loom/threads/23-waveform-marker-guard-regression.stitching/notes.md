# notes — 23-waveform-marker-guard-regression

## Outcome

All four collected red guards are settled: **every one was a stale guard, none
was a runtime defect.** Three were repaired in place (the fourth, the theme pair,
had already been repaired by `21-theme-cyan-tint`). See `decisions.md` for the
diagnosis and the commit behind each.

Guards now green, re-run after repair:

| guard | result |
|---|---|
| `automation-5-waveform-marker/verify_waveform_marker.py` | 19/19 |
| `07-seats-workspace/verify_seats_workspace.py` | 15/15 |
| `07-seats-workspace/verify_seats_workspace_browser.py` | pass |

Run them the usual way — copy out of `.loom/tied/`, run the copy, delete it.

## The sweep, and its evidence

`sweep/` holds the raw results of running all 71 browser-free tied guards
against clean `main`:

- `sweep/results.txt` — first run, executed from a scratch cwd. **Do not quote
  these numbers**: some guards resolve paths relative to the working directory,
  so this run over-reports.
- `sweep/rerun/results.txt` — the reds re-run from the repo root, the way a
  person would. **39 of 71 fail.** This is the trustworthy number.
- `sweep/rerun/*.log` — last 30 lines of each failure.

Kept deliberately: it is the evidence behind `proposal-guard-sweep.md`, and
re-gathering it costs ~15 minutes of wall time.

## Handed to Bob

`proposal-guard-sweep.md` — the broader question the stitch raised (does a
periodic sweep belong in the workflow?), with three rulings requested. Not
built, per the stitch's explicit instruction to raise before building.

The follow-on work is laid out as `.loom/threads/27-tied-guard-rot`, marked
`.waiting` on those rulings. Its recommended first stitch is
`12-dashboard-live-controls/verify_live_controls_backend.py` — three
fleet-overlay mute failures that, unlike everything else sampled, do **not**
look like drift.

## Gotchas

- **Some tied guards cannot be run under the copy-out rule at all** (4 of 71).
  They read sibling files from their own tied directory — e.g.
  `verify_device_alias_wordlists.py` opens `word-list-review.md` next to itself
  — so copying the script alone gives a `FileNotFoundError` that looks like a
  failure but is the rule's fault. Copy the whole directory for those.
- **Run guards from the repo root.** Copying them somewhere and running with
  that as cwd silently changes the answer for any guard using cwd-relative
  paths. This cost me a wrong first number.
- The waveform failure was *not* the timing race it looked like. The awaited
  element does not exist anywhere in the tree — `grep -r` over
  `dashboard/static/` for the selector, before writing any timing theory, is
  what settled it in one step. Check existence before you theorise about races.
