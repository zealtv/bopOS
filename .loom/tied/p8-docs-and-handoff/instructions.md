# p8-docs-and-handoff

Close the polish sweep. Requires p1–p7 tied.

- `dashboard/README.md`: update the Show tab section (global transport,
  exclusive playback, always-forward-synced cues + lead time, drag
  editing, undo, scroll box) and the Patch tab wording (Dashboard,
  no legacy group).
- `.notes/show-tab-design-2026-07-18.md`: confirm the amendment sections
  added by p2/p3/p5/p6 hang together as one readable document.
- `docs/OSC-CONTRACT.md`: the one-line legacy-group amendment note from
  p7 if it wasn't recorded in-stitch (additive; flag, don't redesign).
- `CLAUDE.md`: thread-ordering section — record `15-show-polish` complete,
  `patch-workflow-friction` resumes as next.
- `.notes/handoff-<date>-show-polish.md`: what shipped, verify scripts,
  amendments made to tied verifies, what stays deferred (redo if p6
  deferred it, musical time/curves/etc. still with scene-sequencing).
- Sweep: `grep -ri facilitator dashboard/static` returns only code
  identifiers (no rendered copy), no stale forward-sync references in
  docs.

Verify: run the full show-thread verify set (14-show-tab tied set plus
this thread's) green; docs spot-checked against the running app.
