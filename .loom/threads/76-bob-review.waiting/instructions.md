# 76-bob-review

**Status:** waiting on Bob · collected 2026-10-04 while working the projects queue
**Goal:** one place for everything from that session that needs Bob's review,
ruling or hands on hardware. Agents: don't work this stitch; it's Bob's.

Bob, 2026-10-04: *"anything i need to review put it in a single stitch so i can
look at it all at once after this session"*. Each item points at where the
evidence lives; the stitches named stay where they are. When an item is ruled,
record the ruling in the stitch it points at (resume it if it's waiting), then
move it to Ruled here. Tie this when Open and Hardware checks are empty.

## Open

8. **FYI: my calls on the project menu (66/7)**. Names keep spaces as typed,
   because the folder name is the name ("Kite Choir", as in the mockups):
   letters, digits, spaces, `.` `_` `-`, starting with a letter or digit. New
   error lines follow the existing pattern: "That project could not be
   opened." / "The project could not be created." / "The project could not be
   renamed." / "The site could not be created." Switching project is refused
   outside Live. Say if any of these should change.
9. **Multiple shows (66/10), your calls**. Screenshots are in the lead
   session's scratchpad: `show-menu.png`, `new-show-dialog.png`,
   `show-bar-*.png`, `long-*.png`.
   - **Modes:** confirm the reading of ruling 4. Show switching works in Live,
     Simulation and Patch Edit, and is refused while a step plays *or is paused*.
   - **Wording added:** "That show could not be opened." / "The show could not
     be created." / "… renamed." / "… deleted."; the default show name **Show**.
   - **Show rows have no second line** (projects show Seats·devices, sites the
     room). Add "N steps"?
   - **Header squeeze at 1050–1300px:** four long names ellipsize until the
     header wraps at 1049px. Move the wrap breakpoint to ~1279px (it changes
     the 66/8 layout you approved)? `long-1280.png` shows it.

## Hardware checks (Bob's hands; software halves are done)

1. **Wi-Fi slice 0**: with a Pi up, choose the network manager. The helper
   backend is a marked seam that reports `unavailable` until then. →
   `33b/2-network-config-implementation.waiting`.
2. **Wi-Fi switchover rehearsal**: both APs up, push the list, disable
   *testing*, devices reappear on the hidden show network; disable show 1, and
   the fallback takes over. → same stitch.

## Ruled

1. Passphrase warning wording — **yes**, as it reads in the app (Bob, 2026-10-04,
   via Tengu) → recorded in `33b/2`.
2. Migrate `dashboard/shows/test.json` into the project's `show.json` and delete
   `dashboard/shows/` — **yes** (Bob, 2026-10-04) → recorded in `66-projects/5-one-show`.
3. OSC contract editorial — **rename it** (Bob, 2026-10-04). The facilitator
   allowlist is now "a project-level allowlist in `project.json` … the project
   promotes its verbs" (`docs/OSC-CONTRACT.md` ~859).
4. Venue snapshot `10x8-test` — **drop it** (Bob, 2026-10-04). Removed from
   `dashboard/installations/` (local, gitignored); a copy is in the lead
   session's scratchpad.
5. "New patch…" on the Patches tab — **keep** (Bob, 2026-10-04) → `66-projects/6-patch-versions`.
6. Header tidy screenshots — **look fine** (Bob, 2026-10-04) → `66-projects/8-header-tidy` tied.
7. Clear show — **yes, wording fine** (Bob, 2026-10-04): "Clear Show…", confirm "Remove all N steps from this show? You can undo this." → `66-projects/9-clear-show` (queued).
