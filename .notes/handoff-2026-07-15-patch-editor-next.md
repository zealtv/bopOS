# Handoff — patch editor through PE-3, simulator audio fixed (2026-07-15)

State at handoff: fleet-patch is complete through its real bop000 gate;
patch-editor is complete through PE-3 plus the PE-3b simulator launch-race
fix. The implementation baseline before this notes/manifest handoff commit is
`1ba6cee`; the handoff commit is also pushed on `main`. Loom has no claimed
stitch, 90 tied stitches, and one loose end:
`patch-editor/pe-4-points-and-cues-ui`.

## Start the next session here

1. Read `CLAUDE.md`, this note, and `.notes/running-order.md`; then run
   `./.loom/loom.sh status`.
2. Claim only `patch-editor/pe-4-points-and-cues-ui`.
3. Implement its session-only one-element point scratch setup and cue firing
   through the existing `/pt` and `/cue` paths. Do not persist the scratch
   point setup and do not edit a `.pd` file.
4. Use its focused Playwright capture-socket gate and the adjacent spatial,
   cue, patch-editor, and simulator regressions selected via
   `docs/VERIFICATION.md`.
5. After PE-4 ties, proceed to tabs-0. The hands-on interactive UI/touch audit
   belongs at tabs-2, after tabs-0 is ratified and tabs-1 has installed the
   real tab structure.

## Work completed on 2026-07-15

- `fp-4-bop000-gate`: live fleet Set, fingerprint convergence, induced drift,
  stale detection, Retry, current state, Revert, and audible bonks output all
  passed on bop000.
- `pe-2-edit-mode`: managed, mutually exclusive edit/simulate runtime and live
  editor controls tied; its focused suite passed 27/27 including real GUI Pd
  launch and cleanup.
- `pe-3-manifest-editor`: validated atomic param/cue editing and New Patch tied;
  backend passed 12/12 and browser passed 12/12. Bob's template was copied
  verbatim in verification and never edited.
- `pe-3b-simulator-param-catchup`: diagnosed silent `bonks-pd` simulator starts
  as an early gain catch-up arriving before the Pd patch graph was ready.
  Bounded parameter declaration replays at 1.5 and 4 seconds fixed it. Focused
  verification passed 6/6, adjacent simulation passed 9/9, PE-2 passed 27/27,
  and Bob confirmed audio after a normal simulator start without manual OSC
  gain injection.

Recent commits, all pushed:

- `1ba6cee` — Replay simulator parameters after launch
- `1da889c` — Add patch manifest editor
- `e7a7a3e` — Add managed patch edit mode
- `1c8143a` — Complete fleet patch workflow

## Worktree boundary

Bob's manifest-editor result in `patches/demo-pd/bopos.patch.json` is included
in the handoff commit: it reformats the manifest and removes the `echo`
parameter while retaining `gain0`, `gain1`, and cue `snap`. It is intentional,
not a regression to restore.

Bob's ignored source template is present at
`patches/.templates/bopos-template.pd`, SHA-256
`1a5ef7af383180f11f10796a7ea9f5f38b4a2fdb44f02e7eb742f8d8d322cc81`.
It is intentionally ignored by `patches/.gitignore`. Never edit it or any
other `.pd` file.

## Live launch state at handoff

- The local dashboard is running at `http://127.0.0.1:8080` in detached tmux
  session `bopos-dashboard` (`dashboard/server.py --host 0.0.0.0`).
- Supervisor mode is `off`; the audible simulator gate is complete and no
  managed audition/Pd simulator processes remain.
- Dashboard persisted master is `0.13` after restoring the temporary 0.5
  diagnostic level.
- bop000 (`2c:cf:67:b3:0a:58`, seat 0) is online, reports framework revision
  `1f0a5b9`, and is running `bonks-pd`. Desired and observed patch identity are
  current at fingerprint
  `8c4da2e48d4866c00b31d96da8d94e9f164586b538464fab7135e63ece1b38d3`.
- Browser verification has standing authorization from Bob. Do not ask again
  merely to exercise that standing authorization.

## References and retained edges

- `.notes/running-order.md` is the compact priority runway.
- `.loom/tied/pe-3b-simulator-param-catchup/results.md` records the silent-start
  diagnosis and live gate.
- `.loom/tied/pe-3-manifest-editor/results.md` and
  `.loom/tied/pe-2-edit-mode/results.md` retain their exact verification scope.
- `.notes/handoff-2026-07-14-fleetwide-patch-next.md` retains the detailed
  bop000 lifecycle, JACK, power-control, and legacy-update edges; those remain
  valid unless superseded by later work.
