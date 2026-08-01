# Decisions — 08-editor-save-recall

Date: 2026-07-29. Worked in parallel with `07-control-device-ui`, which owns
the shared decisions about the row itself, the catalog, the save preview, and
the apply broadcast. This file records only what is the editor's own.

## The editor is a seat-shaped target, not a Seat

R1 says one application path. The editor drives OSC selector 0 on the private
audition relay, but it is not Seat 0: it has no Device, no groups, and its
durable mirror is `state.data["editor"]["params"]`. Rather than grow an
editor-only pipeline, the editor is presented to the core as one concrete
target — `Dashboard.editor_target()`, a pseudo-seat with `id: 0` (its wire
selector), `editor: True`, and a `params` dict shared **by reference** with
editor state, so an apply writes straight through to what the panel renders.

`live_param_target("editor", None)` returns it, and only while
`supervisor_mode == "edit"`; outside Patch Edit there is no engine on selector 0
to talk to. `effective_patch_for_seat()` answers the editor's patch for it, so
the core's ordinary patch filter does the right thing without a special case.

Three consequences, each handled explicitly rather than by accident:

- **Automation keys.** The automation table is keyed by `str(seat["id"])`,
  which would put the editor's entries in a real Seat 0's. Targets now carry an
  optional `automation_key`; the editor's is `"editor"`. One helper,
  `preset_application.automation_key()`, is used everywhere the table is read
  or written.
- **Device mirrors.** The editor has none, so `_store_fade_destination()` and
  apply's mirror loop skip the Device pass for an editor target.
- **Provenance.** `applied_preset` / `preset_dirty` live on the pseudo-seat,
  runtime-only exactly like a Seat's, and are mirrored onto the published
  editor block by `publish_editor_provenance()`. `durable()` never serialises
  the editor block at all, so a restart forgets them (A7). Starting a new edit
  session clears them: provenance is a claim about values the engine is
  currently holding.

## Recording moved to the resolved targets

`OSCBridge.record_param(selector, …)` re-derived its targets from the selector.
That cannot work for the editor, and it was already redundant for preset apply,
which resolves its concrete targets *before* deciding whether the send may
coalesce to `all`/`gN`. `record_param_for(seats, …)` now holds the body and
`record_param` delegates to it. Behaviour for every existing caller is
unchanged: coalescing is only permitted when no target was skipped, which is
exactly the case where the selector resolves back to the same set.

## Edit mode blocks fleet control, not this

`apply_preset` is in `edit_blocked_mutations` because it is a fleet execution
control. An `editor`-scoped apply is not: it targets the audition engine Patch
Edit itself owns, so it is the one apply that belongs *inside* edit mode. The
gate is scope-aware in both directions — an editor-scoped verb outside edit
mode is refused with "The patch editor is not running."

## The row, not the tree

The editor keeps its own `editorParamTree` (out of scope here, and the
generator drawer explicitly so). Only the preset row is shared, through a third
`ControlSurface` instance wired with the editor's preset callbacks and
`bindPresets()` scoped to `#editor-params`. That is what makes the editor and
the Control tab read as one language without merging two parameter
implementations.

## Saving must not restage the fleet

This is the workflow the `presets/` fingerprint exclusion exists for, so it is
asserted rather than assumed: `verify_preset_editor.py` records the fleet
patch fingerprint, saves a preset mid-sculpt, waits out a convergence cycle,
and checks the fingerprint is unchanged and the patch is not marked stale.

## Verification

`tests/verify_preset_editor.py` (new) runs the editor headlessly with
`--sim-no-engine --sim-audio-backend none` — `set_edit` reaches a real `edit`
supervisor mode without Pure Data. It covers the row's presence and anatomy,
save capturing the audition engine's state, the fingerprint/staleness
assertion, recall after a nudge (including the datagram reaching the audition
relay), provenance, derived dirtiness, and delete. Fast-tier coverage for the
pseudo-target and the automation-key isolation is in
`tests/test_preset_application.py::PresetSurfaceServiceTests`.

**Real PD/GUI behaviour remains a hardware adoption check.** Nothing here has
been run against Pure Data; what is verified is that the dashboard captures,
stores, recalls, and emits on selector 0.
