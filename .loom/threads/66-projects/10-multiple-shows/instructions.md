# 10-multiple-shows

**Status:** ready · Bob asked for it 2026-10-04 · operator wording below needs his OK
**Goal:** a project holds several shows and one is open; pick, add and rename
them from the project menu in the top bar.

This supersedes the ratified "one show per project" (`0-project-design` rulings
§4) for shows only. Sites still change only geometry.
Bob, 2026-10-04: *"a picker would make sense in the project dropdown in the top
bar - i think i'd like to implement this."*

## Shape (from the 66/5 code survey)

- `show_model` is already per-document; nothing in it changes.
- Storage: `projects/<project>/shows/<name>.json`; `project.json` gains
  `current_show`. Name rules are the project/site ones (spaces kept, the file
  name is the name).
- `state.show_path` follows `current_show`. Opening a show reuses the
  open-project sequence: stop playback, load, clear undo, broadcast. It's
  refused while the show is playing.
- Server actions for new, open and rename show (delete per Q3). The removed
  show-catalog actions in git history (before `8694b8f`) are a reference.
- Migration: an existing `show.json` becomes `shows/<its name or "Show">.json`
  and the current show. One-off and non-destructive, like the 66 tools.
- New project: one empty show, so a project always has a current show.
- Clear Show (`9-clear-show`) acts on the open show; build either order.

## Menu (mockup 4 pattern)

A **SHOW** section after SITE, mirroring it: the current show first and
highlighted, others with **Open**, **Rename** on the current one, and **New
Show**, which opens a dialog with a name and *Start from* an empty show or a
copy of an existing one, like New Site. The bar stays *Project · Site · Patch*;
the open show's name is the Show tab heading.

## Questions for Bob (answer before building)

1. Section and button wording: **SHOW** · Open · Rename · **New Show** (dialog:
   Name, *Start from* "An empty show" / "An existing show", Cancel / **Create
   Show**). OK?
2. Leave the bar as *Project · Site · Patch*, or add the show (*… · Show*)?
3. Delete a show from the menu? Recommended: yes, for non-current shows only,
   with a confirm. Wording, e.g. "Delete" with "Delete show "X"? This can't be
   undone."
4. Can shows be opened in Simulation or Patch Edit? Recommended: Live only, the
   same as switching project.

## Verify

Unit tests: storage, migration, open/new/rename/delete, and refusing during
playback. A browser journey for the menu section and dialog, opening a second
show, and the Show tab following it. Fast and browser suites.
