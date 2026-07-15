# Dashboard information architecture proposal (tabs-0)

Status: **ratified by Bob on 2026-07-15, with the admin-command scope amendment
recorded below**. This proposal incorporates Bob's
2026-07-15 session notes and supersedes the stitch brief's provisional
Overview / Spatial / Fleet management / Patch editor names. It changes
navigation and placement only; interaction redesign belongs in `tabs-2`.

## The organising rule

- **Dashboard** is operating the piece now.
- **Seats** is authoring the installation's places and spatial behaviour.
- **Devices** is observing and administering hardware and the live fleet.
- **Patches** is authoring and managing patch content on the host.
- **Assets** and **Sequencer** reserve the next two content domains without
  pretending their workflows are designed yet.

This replaces the separate "facilitator" and "technical" destinations. The
facilitator surface becomes the **Dashboard** tab; the other tabs are the
technical/authoring surfaces in the same shell. The word "facilitator" remains
an internal manifest/contract term for promoted controls, not a navigation
label. The existing `/facilitator` URL should remain as a compatibility entry
that opens Dashboard.

Recommended tab order: **Dashboard · Seats · Devices · Patches · Assets ·
Sequencer**. Dashboard is the default landing tab.

## Tab map

### Dashboard

The touch-first live surface, renamed from Facilitator:

- fleet master and **Silence All / Resume**;
- one card per occupied seat/device with the patch parameters marked
  `facilitator: true`;
- an **All devices** control for each promoted parameter, using the existing
  `/all/p/<name>` path, alongside individual controls;
- declared cue buttons and the existing free-text/synchronised cue fire
  control;
- preset save, load, rename and delete for live mix snapshots;
- explicitly promoted framework commands such as restart engine, reboot and
  shutdown, with the existing confirmation/hold safeguards; each promoted
  command exposes both a fleet-level action and a single-device action;
- compact health and fleet-patch warnings that link to Devices for action.

Promotion has two sources, preserving the ratified contract boundary:

- Patches marks patch parameters for Dashboard with `facilitator: true`.
- The venue/installation allowlist promotes framework commands. Its editing
  affordance belongs with fleet administration in **Devices**, not in the
  patch manifest: the patch promotes its parameters; the venue promotes its
  verbs. Promotion makes the verb available at two explicit scopes: fleet-wide
  for setting up or operating a fleet, and per device for onboarding or
  remediating one box. Scope is chosen at action time; it is never inferred
  from whichever device card happens to be selected.

Dashboard should optimise the arrangement after the skeleton exists; the
touch/UI review remains deliberately deferred to `tabs-2`.

### Seats

The authored installation model:

- the full map and seat list;
- room dimensions, datum, seat creation, naming, binding shortcuts and
  true-N element positions;
- authored points, their list, geometry, falloff and motion;
- listener puck while simulation is active;
- venue save/load and venue-level settings;
- the **Simulate** action, because simulation inhabits the authored seats and
  previews this venue.

Simulation remains the already-ratified global supervisor mode, mutually
exclusive with patch editing. Its active state is visible in the global shell
on every tab, but the action to enter/leave it lives in Seats. Patches may keep
the contextual "Hear it in the sim" handoff already designed.

Venue files contain the preset library, fleet-patch choice and Dashboard
command allowlist as durable installation state, but venue save/load is not
where those things are operated day to day.

### Devices

The observed boxes and fleet operations:

- active devices first, plus recently active/offline devices with last-seen
  state; unbound devices remain visible;
- identity, hostname, uid, IP, assigned seat, online/engine health, version,
  capabilities/report facts and Identify;
- bind/unbind/forget and a jump to the corresponding Seat;
- individual guarded administration (restart engine, update bopOS, reboot,
  shutdown, patch/content diagnostics);
- live-fleet bulk administration and configuration of which allowed framework
  commands appear on Dashboard at fleet and single-device scope;
- the single desired **fleet patch** selector, Set/Retry/Revert operations,
  convergence summary, and per-device current/switching/missing/mismatch/stale
  diagnostics.

Fleet patch control belongs here because setting it is a deployment and
convergence operation. Patches may link to "Deploy via Devices", but must not
grow a second fleet-patch authority.

Device detail retains observations, diagnostics and remediation. It does not
regain per-device patch selection, spatial authoring, or ordinary mix controls:
those are fleet-scoped, Seat-scoped and Dashboard-scoped respectively.

### Patches

Host-side patch content and the existing editor:

- host patch catalog, create, inspect and remove/manage actions;
- open/relaunch/restart the one-device edit session;
- live parameter test panel and master for that private edit target;
- manifest parameter and cue declaration editing, including parameter
  Dashboard promotion;
- session-only point scratch map and cue firing used to test the open patch;
- a link/hand-off to fleet deployment in Devices, not embedded fleet controls.

The editor's points and cue buttons stay here because they are private scratch
tools. Production points live in Seats; production cue firing lives in
Dashboard. Cue declarations live in Patches.

### Assets (placeholder)

A visible placeholder for loading, cataloguing, inspecting and eventually
converging host assets across the fleet. No controls are invented in tabs-0.

### Sequencer (placeholder)

A visible placeholder for the Ableton-style show-control sequence system. Its
language and interaction remain a Bob co-design gate; no sequencing behaviour
is implied by the tab skeleton.

## Global shell

Keep globally visible only what establishes context:

- tab navigation and installation/venue name;
- dashboard connection state and a compact live-device/health summary;
- supervisor target/mode: live fleet, simulation or patch edit;
- the safety-critical Silence All state/action while the live fleet is the
  active target.

Master is not a context-free global control: Dashboard master controls the
piece, while Patches has the edit rig's master. Labelling those targets is safer
than one slider whose meaning changes with supervisor mode. Detailed status and
all ordinary actions stay inside their owning tab.

## Presets, venues, points and cues

The similar-looking concepts stay distinct:

| Thing | Authored/managed in | Used in |
|---|---|---|
| Venue (room, seats, bindings and durable installation state) | Seats | Seats; loaded state feeds all tabs |
| Production points | Seats | Spatial behaviour of the live/simulated piece |
| Patch scratch points | Patches | Current private edit session only |
| Cue declarations | Patches | Dashboard and future Sequencer |
| Manual/synchronised cue fire | Dashboard | Live performance |
| Presets (master + per-seat parameter snapshots) | Dashboard | Dashboard; library rides in venue saves |
| Fleet patch desired state | Devices | Fleet and simulation; choice rides in venue saves |

## Ratification boundary

Ratifying this proposal approves the six tab names/order, the ownership map
above, removal of the facilitator/technical navigation split, and the proposed
placements for Simulate, fleet patch, points, cues and presets. It does not
approve a visual redesign, the Assets workflow, or Sequencer semantics. Those
remain later work.

## Ratification record (Bob, 2026-07-15, verbatim)

> that boundary is ok - but we want to be able to specify admin dashboard
> commands at a fleet level, as well as at a single device level. fleet level
> would be setting up a fleet, single device level would be for onboarding a
> new device. Otherwise this is looking good.

Applied as: the patch/venue promotion boundary is ratified. Every venue-promoted
admin verb is available on Dashboard through two deliberately labelled action
scopes—fleet and one selected device—while preserving the verb's existing
confirmation or hold-to-confirm guard. The six-tab IA is otherwise ratified as
proposed.
