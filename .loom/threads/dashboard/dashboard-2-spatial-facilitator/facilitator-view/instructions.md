# facilitator-view

**Decision gate (CLAUDE.md): user-facing facilitator choices are Bob's to
ratify.** Write the design proposal first, mark this stitch `.waiting`,
surface it to Bob; build only after ratification.

Scope (from `.notes/dashboard-development-context.md` §9 + phase-2 checklist):
- `/facilitator` view: per-device volume cards, touch-first for iPad,
  PWA manifest (add-to-home-screen fullscreen)
- Master volume (semantics need ratifying: proportional scale vs absolute)
- Silence All (panic button), Start All
- Preset system: save/load named partial states; created by technician,
  used by facilitator (preset data model can be ratified here too)

The proposal must reconcile the pre-contract design doc with what the
contract era changed: params are now manifest-declared (`/p/<name>`), not
hardcoded gain/gain2/backing — so "volume card" needs a defined mapping
(which declared param is "the volume"? manifest `group: "mix"`? a designated
`primary` flag?). That mapping is exactly the kind of user-facing call the
gate exists for.
