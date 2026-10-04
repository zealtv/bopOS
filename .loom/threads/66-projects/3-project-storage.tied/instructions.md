# 3-project-storage

**Status:** after `2`
**Goal:** state lives in `dashboard/projects/<project>/` with the device
registry host-global in `dashboard/devices.json`; still one project, no
switching. The global project bar appears, read-only.

Spec: `../0-project-design/proposal.md` (ratified 2026-10-04; names and choices in `../0-project-design/rulings.md`).
Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit; leave the system working.

- Layout and field mapping: proposal §2 and §4. `project.json` (seats, groups,
  `next_group_id`, Patch, master, `event_lead_ms`, Remote device commands);
  `devices.json` (registry minus `desired_patch`); gitignore
  `dashboard/projects/`, `dashboard/devices.json`, `dashboard/current-project`.
- **One-off migration** (proposal §6) as a tool run once: `installation.json`
  → the first project; a `default` site comes in `4`, so positions stay on
  Seats for now. Then delete the `installation.json` code path — no
  compatibility layer.
- Remote device commands stop being labelled a venue setting.
- Read-only project bar in the header: *Project · Site · Patch* (mockup 0;
  site shows the room until `4`).
- The `--state-file` flag and its callers (tests, `simfleet`, journeys) change with the layout.
