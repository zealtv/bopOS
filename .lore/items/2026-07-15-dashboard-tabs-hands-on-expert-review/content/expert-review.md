# Independent senior UX/UI review — interactive installation workflow

Review date: 2026-07-15. Scope: Bob's live tabs-2 observations, candidate
composition/installation workflows, the ratified IA, tabs-1 screenshots and
current dashboard implementation. The reviewer made no repository edits.

## Executive recommendation

The top-level destinations are sound, but the mode labels describe an
**execution target**, not a general application mode:

- **Live fleet**
- **Simulation**
- **Patch edit**

"Edit" alone is too broad because seats, venues and manifests are authored
throughout the application. Promote the passive target pill into a persistent
top-bar control. Live fleet and Simulation can be entered there. Patch edit
should navigate to Patches when no patch is selected rather than guessing what
to launch. Transitions need explicit target confirmation and must visibly
reassert target/master/mute state. Remove "Edit this patch" from Seats.

The stale cards after Simulation stops are a release-blocking state-coherence
bug, not visual polish. The embedded Dashboard has a second WebSocket/render
lifecycle, making late simulator updates especially important to regression
test.

## Recommended ownership

| View | Owns | Does not own |
|---|---|---|
| Dashboard | Live/sim mix, master, presets, production cue firing, promoted params and guarded promoted commands | Seat authoring, device identity, patch deployment |
| Seats | Seat create/delete/name/ID/position, production points, room, venues, map-first binding | Device diagnostics, patch params, hardware version |
| Devices | Physical inventory/health/version, network/engine state, Identify, reboot/shutdown/update, device-first binding, content drift and one-click recovery | Seat geometry/names, ordinary mix, choosing the production patch |
| Patches | Host catalog, create/edit, private audition, manifests/cue declarations, choose and deploy production/fleet patch | Per-device repair details |
| Assets | Host asset catalog, desired fleet assets, deploy/sync progress | General device administration |
| Sequencer | Future authored show control | Current manual cue firing |

Move desired fleet-patch selection/deployment to Patches. Devices retains
observed-versus-desired state and one-button **Sync to fleet patch** repair.
There remains exactly one desired-state authority: this relocates its control;
it does not introduce a second selector. Apply the same content/exception
pattern later to Assets.

Binding legitimately crosses Seats and Devices but remains one operation over
one binding record:

- Map-first: select Seat → choose/scan unbound device → Identify → Assign.
- Device-first: select unbound device → Identify → assign to an empty Seat.
- Seat properties are editable only in Seats.
- Device properties/actions remain available regardless of binding.

Venue state should contain room, seats, bindings, production points, presets,
production patch choice and the promoted-command allowlist. Current
`InstallationState.durable()` excludes production points, contradicting that
workflow and creating a data-loss risk.

Presets are seat-targeted. Dashboard cards should therefore use **seat name**
as their primary identity, not MAC, hostname or future board alias.

## Skeleton critique and failure risks

Devices still contains most of the old monolithic surface: fleet selection,
duplicated rosters, seat edit/bind/position, patch params, assets, diagnostics
and actions. Selecting an object therefore does not produce a predictable kind
of detail.

- `bindDeviceToSeat()` explicitly copies a default seat's hostname: remove it.
- One real device appears twice because unbound is a second list rather than a
  status/filter: use one canonical entry.
- Unbound detail returns early and hides normal administration.
- Unique unbound reboot/update/patch commands are not merely hidden: the wire
  selector is `all | seat ID`, all unbound boxes share `-1`, and Identify works
  only through its special uid payload. Design the UID-target seam first.
- `patch_switch` remains true until `/os/rev`; a lost/unattributable receipt
  means indefinite Switching. Add a bounded operation state, timeout/failure,
  final refresh and Retry.
- If seat renumbering is supported, it is an explicit migration in Seats that
  updates preset references and related state, never a casual Device field.
- Shorten fingerprints to their final 8–12 characters and copy the full value.
- Add guarded Shutdown All and keep Identify immediately visible.
- Treat the global target as a control, not passive decoration.

## Recommended journeys

### Composition

1. Create/select a patch in Patches while drafting seats/positions in Seats.
2. Enter Patch edit for private param, cue and scratch-point testing.
3. Exit to Simulation through the global target control.
4. Adjust production positions/listener/points in Seats.
5. Test promoted params, production cues and presets in Dashboard.
6. Return to Patches for code/manifest changes; repeat.

Simulation auditions a deliberately selected working patch and must not
silently change the desired live-fleet deployment.

### Installation day

1. Load venue in an explicit safe Live fleet state.
2. Discover one device roster; inspect versions/health and update as needed.
3. Assign from the Seats map or device detail; Identify at each position.
4. In Patches choose **Deploy as fleet patch**.
5. Watch convergence; repair exceptions in Devices with **Sync to fleet patch**.
6. In Assets deploy desired assets and repair exceptions the same way.
7. Test cues/params in Dashboard; tune and save presets.
8. Use guarded fleet shutdown from Devices after the session.

## Human-readable physical device identity

"Freda Sparks sits in Seat 0" is a strong metaphor. Make that a device alias,
distinct from hostname and seat name:

- deterministic curated two-word default from stable uid;
- stored, operator-editable alias in the host device registry;
- display `Freda Sparks · Seat 0`, hostname and uid tail secondary;
- collision resolution and a curated safe/easily-heard word list;
- full uid behind copy; alias never copied into seat name.

Defer this to its own stitch. Until then, bound devices show seat name primary,
hostname secondary, uid tail tertiary. Unbound devices show hostname primary +
uid tail and explicitly handle duplicate hostnames.

## Priorities

### Must-fix correctness

1. Simulation stop clears virtual cards and restores live state without refresh.
2. Remove hostname-to-seat auto-renaming.
3. Replace indefinite Switching with timeout/error/retry.
4. Persist production points in venues.
5. Reset selection/detail coherently after binding/removal/mode transitions.
6. Render Dashboard cards by seat and visually verify preset targeting.
7. Regression-test rapid Simulation/Patch edit → Live transitions, including
   late updates and target/master/mute correctness.

### IA corrections

1. Global Live fleet / Simulation / Patch edit control; remove cross-link.
2. Move seat authoring to Seats; dual-entry binding over one record.
3. One device roster; full bound/unbound device detail after UID targeting design.
4. Choose/deploy fleet patch in Patches; drift/repair in Devices.
5. Resume framework-version currentness for Devices.
6. Shutdown All and direct Identify in Devices and commissioning shortcut in Seats.

### Polish/later

1. Short hashes with copy.
2. Human device aliases.
3. All-seat promoted-param controllers on Dashboard.
4. Flatten the embedded Dashboard if its duplicate lifecycle remains costly.
5. Review spacing/touch density after the model stabilises.
