# 9-clear-show

**Status:** ready · Bob ruled 2026-10-04 (wording approved)
**Goal:** start the project's one show fresh without making a new project.

Proposal §3: "to start fresh, clear it or make a new project". Bob, 2026-10-04:
*"clear show is good. wording is fine."*

- **Button:** "Clear Show…" in the Show header beside the play, stop and next
  controls, styled like the other destructive actions. Shown only when the
  show has steps.
- **Confirm:** "Remove all N steps from this show? You can undo this." N is
  the step count, with plurals handled.
- **Effect:** one `show_model` mutation that empties `items`, run through
  `apply_show_mutation`, so it's saved, broadcast and undoable like any other
  edit (`show_undo`). The show name, project, Seats, groups and patch are
  untouched.
- Refused while the show is playing, like other show edits.
- Tests: a unit test for the mutation and undo; a browser check for the
  button, the confirm and undo.

**Bob, 2026-10-04 (after build):** one-step confirm wording fine; refusal "Stop the show before clearing it." approved.
Bob: "1 steps" would also be acceptable if pluralising ever complicates code; kept the singular since it is one conditional.
