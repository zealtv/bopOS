# 68-remove-git-patch-route

**Status:** verified · Bob ruled 2026-10-03 · phase 2 complete
**Goal:** patches reach devices one way only — dashboard push. The Git route
is gone from node, dashboard, simulators, docs and tests.

Bob, 2026-10-03: *"let's remove the git route for the moment."* Removal, not
deprecation: no compatibility shim (the `/cue` retirement is the precedent).
Evidence: `lore:2026-10-03-bopos-code-review-2026-10` (§ Complexity).

## What goes

- **Node** (`python/bopos.py`): `addpatch` and `pullpatch` verbs
  (`add_patch_callback`, `pull_active_patch_callback`,
  `_PULL_ACTIVE_PATCH_PHASES`), the engine `/admin update-patch` action, the
  `git pull` inside `switch_patch_callback`, the "refusing to fetch into a
  git-managed patch" branch in the fetch worker, and the `git` field in the
  `/os/patches` listing.
- **Script:** `bash/pull_active_patch.sh` (it also forced a full reboot and
  hard-coded `/home/pi/bopOS`).
- **Dashboard:** `add_patch` / `pull_patch` handlers, git-managed skips in
  distribution (`device_patch(..., git=True)`), the "Pull latest" button in
  `dashboard.js`, and the `git` field in `osc_bridge`'s patch-listing cleaner.
- **Simulators:** matching verbs in `tools/simfleet.py` and `tools/audition.py`.
- **Elsewhere:** check `python/io/sys_info.py` and `python/runcontext.py`
  (they read git for *framework* revision — likely keep, confirm).
- **Docs:** contract §7, `docs/OSC-REFERENCE.md`, `docs/COMPOSING.md`.

## What stays

Framework update over git (`updatebopos`, `checkout`, `converge_framework`) is
a different thing — bopOS itself, not patches. Keep it.

## Decide in-stitch

- A device that already has a git-cloned patch dir: after removal it's just a
  directory. Say whether push overwrites it, and test that.

## Done when

- `git grep -E "addpatch|pullpatch|pull_patch|add_patch|pull_active_patch"`
  finds only history (§15, lore, loom records).
- Contract amendment with a §15 entry — proposed to Bob before landing, since
  it's the wire. `docs/PORTS.md` unaffected.
- `tools/run-tests.sh fast` + `browser` green.
