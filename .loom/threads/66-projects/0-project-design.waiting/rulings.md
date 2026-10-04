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
