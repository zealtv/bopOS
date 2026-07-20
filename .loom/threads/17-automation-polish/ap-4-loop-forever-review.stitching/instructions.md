# ap-4-loop-forever-review — is the per-step "loop forever" needed?

**Bob, 2026-07-20:** "I don't think we need the loop forever button on a
step, since we can just set the step to play again. Have a think to see
if there's any reason why we might need the loop forever toggle."

The control: `#show-play-forever` checkbox ("loop forever") in the Show
tab (`dashboard/static/js/show.js:476`, handled ~line 1218), with
whatever backing field exists in `dashboard/show_model.py` /
`show_engine.py`.

## Do

1. **Think first, in writing.** Enumerate what "loop forever" does that a
   step whose then-action re-triggers itself cannot: consider the full
   then-action vocabulary, the new global transport + cue lead time
   (15-show-polish), exclusive one-step playback, stop semantics (how do
   you *stop* a self-retriggering step vs a looping one?), and editing
   ergonomics. Write the analysis into this stitch (`analysis.md`).
2. **Ruling (Bob, 2026-07-20): remove it if unneeded.** If the analysis
   finds no capability gap, remove the checkbox and its playback-engine
   branch. Existing show JSON files containing the loop flag must still
   load (ignore the field gracefully, or migrate on load) — Bob has real
   shows in `dashboard/shows/` (untracked; **never** `git add` that dir).
3. If the analysis *does* find a real gap (e.g. stopping semantics
   differ in a way operators need), keep the control, and notify Bob of
   the reason in the session report + handoff.

## Verify

If removed: house Playwright verify that a legacy show file with the loop
flag loads and plays, the checkbox is gone, and a self-retriggering step
actually loops and can be stopped from the transport. If kept: no code
change; the analysis is the artifact.
