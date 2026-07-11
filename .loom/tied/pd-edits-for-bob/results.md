# PD rewrite-wave results

Bob completed the Pure Data OS-layer and reference-patch rewrite wave recorded
in `.notes/pd-edits-for-bob.md`.

Landed:

- helper lifecycle/provision forwarding including `restart-engine` and
  `checkout`, with a whitelisted local notification bus;
- helper `identify`, `/pt`, and `/cue` delivery;
- retirement of PD heartbeat/aloha emitters;
- selector-stripped patch-plane routing;
- `bopos.out~` master plus belt-and-braces mute and notifications;
- `bopos.point` point/element routing;
- a reference cue and synthetic role-meter example; and
- the per-instance `BOPOS_ENGINE_PORT` audition surface.

The real Mac gate launched three PD/CoreAudio instances with distinct local
ports and heartbeats. Bob audibly confirmed point-controlled element-0 noise
on the left channel and identify notifications on both channels. Full commands,
automated assertions, and limitations are retained in tied
`audition-1b-pd-mac-gate`.

Deliberately deferred design work is not pending PD editing: identity/run
context, the `bopos-` local namespace, command/IO process boundaries, legacy
debug/echo paths, and meter semantics/subscription. The verbatim source and
question brief live at:

- `.lore/items/2026-07-11-pd-engine-boundary-brain-dump/`
- `.notes/pd-engine-boundary-design-brief.md`

Known platform limitation: PD's legacy broadcast report connection to
`255.255.255.255:5550` failed with macOS error 49 during the audition run, so
dashboard arrival of the synthetic meter was not verified. This is recorded
for the design session rather than silently treated as working.
