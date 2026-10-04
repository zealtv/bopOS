# Rulings during the design session

Bob's answers while co-designing; `proposal.md` builds on them.

## 2026-10-04 — the model

Framing put to Bob: a project folder replaces `installation.json`,
`installations/` and `shows/`; one project open at a time; the host device
registry (aliases, enabled) stays host-global, outside projects.

1. **Seats per project.** Seats, groups and Seat bindings (which box sits at
   which Seat) belong to the project, like voices in the composition. A site
   holds only the room, listener and Seat positions. One show runs at every
   site unchanged.
2. **Patch iterations are patch folders.** The project lists patch folders
   (e.g. `kite-v1`, `kite-v2`) and marks one live. Patch edit works on a
   folder; pushing it makes it live.
3. **The fleet is the boxes bound to the project's Seats.** No separate
   device list.
4. **One show per project.** Sites change only geometry.

## 2026-10-04 — naming and the open questions

- **Names: Project · Site · Patch.** Bob: *"since the live iteration patch is
  based on folder name - rather than calling it "live iteration" it should
  simply be "patch" … probably "Patch" to go with "Project" and "Site"."*
  The project's other patch folders are its versions.
- **Boxes outside the open project: unassign them** on opening a project.
- **Remote device commands are a project setting.**
- **New Version** makes a new folder (copy of the Patch); the dashboard
  suggests a folder name. Bob: *"We should still be able to edit and update
  the current patch with out a version bump."*
- **Mockups:** yes, from the running app, after the text review.

## 2026-10-04 — mockup review, round 1

- **Patches tab: a dropdown or sidebar list** — "we could end up with a lot of
  patches". → Sidebar + detail, like Devices.
- **"Make It The Patch" is clunky** — Bob suggested "Set Live" or "Set
  Active". → **Set Live**, with a **Live** tag on the running patch; it pairs
  with the Live mode.
- **Remote device commands on the Patches page**, not in the project bar menu.
  → Patches tab sidebar, as a project setting.
- **"Live Fleet" → "Live"**, and reconsider the mode switch's position and
  padding. → Moved beside the project bar; 30px pill, 5px clear of the header.
- **New Site** shouldn't say "copy current"; a dialog asking whether to base
  it on an existing site. → New Site dialog with *Start from*.

## 2026-10-04 — mockup review, round 2

Bob: *"mockups look good. project and patch tabs much improved. the radio
button is better - top bar is still a bit messy but fine for now"*.
The header tidy (slice 8) stays a later pass; the round-2 layout is good
enough to build on.

## Ratified — Bob, 2026-10-04

*"yes, ratify it and set up the build stitches"* — the proposal as revised
(round-2 mockups) is ratified. Build stitches `1`–`8` follow its §7 order.
