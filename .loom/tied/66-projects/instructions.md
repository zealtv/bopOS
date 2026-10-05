# 66-projects

**Goal:** a **project** is the one thing an operator opens: a composition with
its fleet, its patch (and that patch's iterations), its sites and its show. The
dashboard and code get simpler because of it — not more complicated.

**Status:** design ratified by Bob 2026-10-04 (`0-project-design/proposal.md`).
Building in slices `1`–`8`.

## Bob, 2026-10-03

> "I'm kind of envisaging a project as a composition that contains a fleet and
> might have several iterations of a patch, and might have several sites. So
> for example in Kite Choir, we've got a composition. That composition might
> see several iterations. We tend to be working with the same fleet and we will
> be performing at multiple sites."

> "At the moment we have sites and patches and … show steps, and that's all
> kind of disparate. So finding a way to tidy that up."

> "If we have a project that has an associated patch or set of patches and a
> dedicated fleet, then we don't need to have different patches running on
> different devices. We can simplify things so we assume there is a single
> patch running on every device on a fleet, and we can let go of the idea of
> swapping patches live. Basically, what I'm trying to do is simplify things
> here so we get a clean surface that's easy to work on, and simplify the code
> base as well."

## What this retires (direction, to be confirmed in `0`)

- Per-device patch pins (`set_device_patch` / `clear_device_patch`,
  `patch_pinned`, 📌 markers, "Pin to device", "Follow fleet patch").
- Swapping patches live on a running fleet.
- The scattered pieces a project would own: `installation.json`
  (`fleet_patch`, `params_patch`, `current_show`, seats, groups, room), venue
  snapshots in `dashboard/installations/`, shows in `dashboard/shows/`, the
  patch picked in the Patches tab.

## Related work

- `58-patch-push-workflow/1`, `/3` — push and push-target UI. Re-scope or drop
  once `0` is ratified; they're anchored on it.
- `34-fleet-patch-global-state` (dropped into this thread) — Bob wanted the
  fleet patch visible from every tab. In a project, the project *is* that
  global state.
- `62-split-elements` — its "same patch in every instance" non-goal agrees with
  one patch per fleet.
- `scene-sequencing/show-lanes-and-scenes-design` — the next Show model would
  live inside a project.
- `fleet-testing/spatial-audio/northern-broadwalk-site-plan` — a natural first
  site of the Kite Choir project.
- `65-remove-presets` — do first, so the design needn't model presets.

## Stitches

- `0-project-design` — the model, what it replaces, the operator surface (ratified).
- `1-remove-device-pins` — pure deletion.
- `2-drop-params-patch-and-revert` — controls follow the fleet patch.
- `3-project-storage` — project folder + devices.json, one-off migration, read-only project bar.
- `4-sites` — positions into sites; venue bar goes.
- `5-one-show` — one show per project.
- `6-patch-versions` — Patches tab as sidebar + detail, Live / Set Live / New Version.
- `7-project-menu` — open/new/rename projects and sites; unassign boxes outside the project.
- `8-header-tidy` — Live rename, mode switch placement and sizing.
