# dist-4 results

The tracked demos now live at `patches/demo-pd` and `patches/demo-sc`.
`patches/default`, the repository `templates/` directory, and the PD demo's
patch-level `bopos.config` are gone. `active_patch.txt`, simfleet, audition,
current docs, active stitch instructions, and retained executable regressions
use the new names. The PD demo declares no asset slots because its shipped
synthesis consumes none; the exact Bob-owned asset-context follow-up is in
`.notes/pd-edits-for-bob.md`.

## Verification

- `~/.venvs/bopos/bin/python python/manifest.py patches/demo-pd` — pass,
  selects `pd` / `main.pd`.
- `~/.venvs/bopos/bin/python python/manifest.py patches/demo-sc` — pass,
  selects `sclang` / `main.scd`.
- `~/.venvs/bopos/bin/python
  .loom/threads/patch-asset-sync/dist-4-demos.stitching/verify_dist4_demos.py`
  — pass: 16 focused static/dashboard checks. The real dashboard and one
  simfleet node served both demos; Chromium sent `demo-sc`, observed it in the
  installed dropdown, and issued the exact `os/patch demo-sc` switch. Screenshot:
  `dist4-demos.png`.
- `~/.venvs/bopos/bin/python
  .loom/tied/dist-3-dashboard-send/verify_dist3_dashboard_send.py` — pass: all
  26 retained Send/Sync/drop/switch-adjacent checks after updating its fixture
  from `default` to `demo-pd`.
- `~/.venvs/bopos/bin/python
  .loom/tied/boundary-5-launch-context-and-topology/verify_launch_context.py`
  — pass: 68/68, including `bopos-context patch demo-pd`, asset context, relay
  sockets, launchers, and SC source.
- `~/.venvs/bopos/bin/python
  .loom/tied/preview-2-engine-adapters/verify_engine_adapters.py` — pass: 73
  checks against the moved SC demo.
- `python -m py_compile` passed for `tools/simfleet.py`, `tools/audition.py`,
  the focused verifier, and the updated dist-3 verifier.
- `git diff --check` — pass.
- The worktree `patches/demo-pd/main.pd` blob is
  `749c94bdc6b636ffeb845ae204e9790a98ae0c6e`, exactly equal to
  `HEAD:patches/default/main.pd`: the PD file was moved, never edited.

## Honest boundaries

- `sclang` is not installed on this host, so `demo-sc` was manifest/source/
  launcher checked but not launched or heard.
- No real Pi transfer, engine restart, audio, or installation hardware was
  exercised; the focused integration used the real dashboard with simfleet.
- Three older retained verifiers still encode superseded history unrelated to
  this rename: `patch-manifest` expects the removed no-manifest fallback,
  `boundary-4-pd-edit-wave` expects an older dynamic `netreceive` spelling,
  and the role-removal browser half looks for the retired `gain` selector (the
  latter is already documented in the 2026-07-14 handoff). Their relevant
  manifest/path checks passed; they are not claimed as green suites.
