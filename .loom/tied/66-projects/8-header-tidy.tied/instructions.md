# 8-header-tidy

**Status:** ready · independent of the other slices
**Goal:** the header reads as one statement and is tidy.

Spec: `../0-project-design/proposal.md` (ratified 2026-10-04; names and choices in `../0-project-design/rulings.md`).
Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit; leave the system working.

- Rename the mode *Live Fleet* → **Live** (Live · Simulation · Patch Edit).
- Move the mode switch beside the project bar (once `3` adds it; before that,
  fix sizing in place). 30px pill, 5px clear of the 40px header, 24px buttons
  — today it's 38px, 1px from each edge (mockup 0).
- Bob, 2026-10-04: the top bar *"is still a bit messy but fine for now"* — a
  further tidy pass is welcome here; show him a screenshot from the running
  app before calling it done.

**Bob, 2026-10-04:** header screenshots "look fine" — done.
