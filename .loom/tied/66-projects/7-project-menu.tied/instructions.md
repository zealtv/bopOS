# 7-project-menu

**Status:** after `4`, `5`, `6`
**Goal:** open, create and rename projects and sites from the project bar
(mockups 4–5).

Spec: `../0-project-design/proposal.md` (ratified 2026-10-04; names and choices in `../0-project-design/rulings.md`).
Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit; leave the system working.

- Menu from the bar: projects (Open, Rename, New Project), sites (Use, New
  Site).
- **New Site** dialog: name + *Start from* an empty room or an existing site.
- **Opening a project** re-sends assignments and groups to its fleet and
  **unassigns online boxes not bound in it** (`/all/os/to <uid> unassign`);
  pushing stays explicit.
- `dashboard/current-project` remembers the open project.
