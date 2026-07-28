# Manifest reorder decisions

## Existing order path

No consumer sorted manifest declarations. `dashboard/server.py` preserves the
validated `params` and `events` lists, and the shared `ControlSurface` plus the
Patch editor preview retain declaration order within their separate parameter
and event trees. The standalone facilitator also maps events in received
order. This stitch therefore changes only Patch-tab authoring UX and uses the
existing manifest save, validation, catalog refresh, and fingerprint path.

## Interaction

- Parameters and events each have their own pointer drag handles.
- Drop positions are calculated only against rows in the originating section.
  Moving over the other section clears the drop target and release is a no-op.
- A committed move splices the existing declaration object within its array.
  It never rewrites `path`, `name`, or the resulting OSC identity.
- A real positional change marks the existing manifest draft dirty. Save
  remains explicit and uses `save_patch_manifest`.
- The active handle takes focus and manifest rendering pauses during the drag.
  This prevents heartbeat/state renders from replacing a captured pointer
  target mid-gesture.
- Near-edge pointer movement scrolls the page so long manifests remain
  reorderable.

## Scope boundary

No wire, schema, backend, or Pure Data change was needed. No `.pd` file was
edited.
