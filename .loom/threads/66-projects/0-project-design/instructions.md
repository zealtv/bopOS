# 0-project-design

**Status:** ready · **design gate** — co-design and review with Bob. Ends in a
proposal he ratifies; mark `.waiting` when it's ready. Don't implement past it.
**Goal:** decide what a project is, what it replaces, and how the dashboard
looks with one open.

Read the parent for Bob's words. The test of every answer: *does this make the
surface and the code simpler?*

## Decide

1. **The model.** Project → composition, fleet, patch iterations, sites, show.
   What is each, and what does each own? Likely shapes to test:
   - **Fleet:** the devices (and Seats?) the project uses. Are Seats per site
     (positions differ per venue) or per project?
   - **Patch iterations:** versions of one patch. Named snapshots, git, or
     fingerprints? Which iteration is "live"? How does Patch edit relate to
     iterations?
   - **Site:** a venue — room, Seat positions, groups, listener, Remote
     commands. Today's venue snapshot is close; say what changes.
   - **Show:** one per project, or per site?
2. **What goes.** Confirm or reject retiring per-device pins and live patch
   swapping (see parent). For each removal, say what the operator does instead.
   Name the verbs, fields, UI and tests that would be deleted.
3. **Map today onto it.** Every field in `installation.json`, venue snapshots,
   shows, the Patches tab's patch choice, assets slots — where each lands, or
   that it's dropped.
4. **The operator surface.** Opening/switching projects, where the current
   project shows globally (the old `34` ask), what each tab becomes. Mockups
   generated from the running app.
5. **Migration.** How today's installation, venues and shows become a first
   project. Prefer a one-off conversion over long-lived compatibility code.
6. **Order.** Implementation slices, smallest-first, each leaving the system
   working.

## Evidence

- `lore:2026-07-13-seats-identity-sim-proposal` — how `installation.json` was
  last split.
- `lore:2026-07-15-dashboard-tabs-hands-on-expert-review` — candidate
  composition and installation workflows.
- `lore:2026-09-25-design-references-2026-07` — entity map.
- `dashboard/state.py`, `dashboard/server.py` (`save_venue` / `load_venue`,
  pins), `dashboard/installations/`, `dashboard/shows/`.

## Constraints

- Patches still reach devices only by push (`glean:manifest-and-patch-distribution`).
- Phrase engine/patch ownership so it survives several engine instances per
  device and a non-Pd engine (`glean:horizon-refactor`).
- Any wire change is a contract amendment for Bob.

## Deliver

`proposal.md` (+ mockups) covering the six points, with open questions listed
for the session. Then mark `.waiting` and surface to Bob.
