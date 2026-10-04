# 5-one-show

**Status:** after `3`
**Goal:** the project has one show, `show.json`; the show picker goes.

Spec: `../0-project-design/proposal.md` (ratified 2026-10-04; names and choices in `../0-project-design/rulings.md`).
Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit; leave the system working.

- Move the current show into the project; remove `current_show`,
  `dashboard/shows/`, and the list/create/load/rename/delete show actions and
  UI. Show format unchanged.
- `dashboard/shows/test.json` has Bob's uncommitted local edits. **Bob,
  2026-10-04: yes** — migrate it, edits kept, into the project's `show.json`,
  then delete `dashboard/shows/` from the repo.
