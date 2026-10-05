# 6-patch-versions

**Status:** after `3`
**Goal:** the Patches tab is the project's patches as a sidebar + detail
(mockups 1–3).

Spec: `../0-project-design/proposal.md` (ratified 2026-10-04; names and choices in `../0-project-design/rulings.md`).
Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit; leave the system working.

- `project.json` lists the project's patch folders; one is the Patch (Live).
- Sidebar: filter, **Live** tag, **New Version**, **Add Existing…**, Remote
  device commands (project setting) below.
- Detail: status; *Edit* + *Push* for the live patch, *Edit* + **Set Live**
  for others; the manifest/editor of the selected patch beneath. The separate
  "host patch" picker and the free fleet-patch picker go.
- New Version: copy the live folder, suggested name bumps a trailing number
  (`kite-v2` → `kite-v3`) or appends `-v2`, editable. Editing and pushing the
  live patch in place stays.
- Wording is ratified (Live, Set Live, New Version, Add Existing…).

**Bob, 2026-10-04:** keep **New patch…** on the Patches tab beside Add Existing….
