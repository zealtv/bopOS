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

3. **OSC contract editorial**: `docs/OSC-CONTRACT.md` (~line 859) still says
   the facilitator allowlist lives in `installation.json`. Since 66/3 it's
   `project.json`. Change the filename only? → `33b/2` notes.
4. **Header tidy screenshot**: look at the new header before it's called done
   (Live rename; mode switch moved beside the project bar as a 30px pill with
   24px buttons; spacing tidied). Before and after, plus light, 900px and
   420px: `66-projects/8-header-tidy.waiting/screenshots/`. Code is committed;
   the stitch is parked until you OK it.
5. **Clearing the project's show**: the proposal says "to start fresh, clear it
   or make a new project". The Show tab has no clear action yet; steps are
   removed one at a time. Want a button? If so, what should it say, e.g.
   "Clear show…" with a confirm? → `66-projects/5-one-show`, possibly `7-project-menu`.
6. **Venue snapshot `10x8-test` not converted**: its Seat ids don't match the
   project's, so `tools/migrate_sites.py` left it in `dashboard/installations/`
   (gitignored, untouched). Make it a site by hand, or drop it? Your local
   project now has the `default` site. Backups: `project.json.pre-sites`
   beside it.
7. **"New patch…" kept on the Patches tab** beside Add Existing…. It isn't in
   the mockups, but without it a project can't create a patch from the
   template. Keep, move or drop? → `66-projects/6-patch-versions`.
8. **FYI: my calls on the project menu (66/7)**. Names keep spaces as typed,
   because the folder name is the name ("Kite Choir", as in the mockups):
   letters, digits, spaces, `.` `_` `-`, starting with a letter or digit. New
   error lines follow the existing pattern: "That project could not be
   opened." / "The project could not be created." / "The project could not be
   renamed." / "The site could not be created." Switching project is refused
   outside Live. Say if any of these should change.

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
