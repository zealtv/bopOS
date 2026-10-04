# 10-multiple-shows

**Status:** ready · Bob asked for it and ruled the questions, 2026-10-04
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
  refused while a show is playing. Allowed in every mode (see ruling 4).
- Server actions for new, open and rename show (delete per Q3). The removed
  show-catalog actions in git history (before `8694b8f`) are a reference.
- Migration: an existing `show.json` becomes `shows/<its name or "Show">.json`
  and the current show. One-off and non-destructive, like the 66 tools.
- New project: one empty show, so a project always has a current show.
- Clear Show (`9-clear-show`) acts on the open show; build either order.

## Menu (mockup 4 pattern)

A **SHOW** section after SITE, mirroring it: the current show first and
highlighted, others with **Open** and **Delete**, **Rename** on the current one, and **New
Show**, which opens a dialog with a name and *Start from* an empty show or a
copy of an existing one, like New Site. The bar becomes *Project · Site · Patch · Show*
(ruling 2).

## Rulings — Bob, 2026-10-04

1. **Wording: yes.** SHOW · Open · Rename · **New Show**; dialog Name, *Start from*
   "An empty show" / "An existing show", Cancel / **Create Show**.
2. **Bar: add the show.** *Project · Site · Patch · Show*. Keep the 66/8 pill
   tidy at narrow widths: check 900px and 420px like 8-header-tidy did.
3. **Delete: yes**, non-current shows only, confirm: `Delete show "X"? This
   can't be undone.`
4. **Modes:** Bob asked why not in Simulation; reasoned through and recorded.
   Switching *project* is Live-only because Simulation and Patch Edit run
   engines built from the project's Seats, site and patch. A *show* is only a
   running order (steps sending to groups by name). It changes none of those,
   and show edits are already allowed in every mode. Simulation is the
   rehearsal mode where comparing running orders matters most. **So: opening
   a show is allowed in Live, Simulation and Patch Edit, and refused only
   while a show is playing.** The same goes for new, rename and delete. Undo
   history is per show and cleared on switch. (Bob to confirm this reading;
   build to it.)

## Verify

Unit tests: storage, migration, open/new/rename/delete, and refusing during
playback. A browser journey for the menu section and dialog, opening a second
show, and the Show tab following it. Fast and browser suites.
