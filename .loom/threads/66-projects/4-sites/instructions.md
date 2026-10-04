# 4-sites

**Status:** after `3`
**Goal:** sites hold room, listener and Seat positions; the venue bar goes.

Spec: `../0-project-design/proposal.md` (ratified 2026-10-04; names and choices in `../0-project-design/rulings.md`).
Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit; leave the system working.

- `sites/<site>.json`; Seat positions move out of Seats into the current site;
  `current site` in `project.json`.
- Changing site re-sends `/all/os/assign` with that site's positions (no wire
  change).
- Remove `save_venue` / `load_venue` / `read_venue`, `installations/`, the
  venue bar (mockup 6). Migrate existing venue files to sites when Seat ids
  match; report the rest.
- Site select + New Site dialog arrive with the project menu in `7`; until
  then a minimal site picker is fine.
