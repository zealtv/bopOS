# bopOS running order — quick reference

Last reconciled: 2026-07-15 against live Loom and the handoff/design chain from
the 2026-07-13 composer-experience brain dump.

This is the human-readable priority runway. `./.loom/loom.sh status` remains
authoritative for claims and live stitch state; `CLAUDE.md` remains authoritative
for repository rules. Work one stitch at a time using claim → work → tie.

## Current position

The brain-dump spill through dashboard UI, patch/asset distribution, seats,
managed simulation, and fleet-wide patch software is complete. Patch-editor
design and its v1.4 cue contract amendment are also complete.

The bop000 fleet gate is complete and audibly confirmed. Patch editor PE-0..4
is tied, including the real GUI-PD gate, manifest authoring, point/cue scratch
UI, and the PE-4b live-delivery/element-target follow-up. Bob confirmed point
and cue messages in the opened patch. The next stitch is
`ui-tabs/tabs-0-ia-proposal`; Bob will give its clean context additional notes
before work starts.

## Running order

1. **Complete:** `fleet-patch/fp-4-bop000-gate` — Bob/hardware gate: prove fleet Set,
   convergence, content fingerprint equality, induced drift, `stale`, Retry,
   `current`, and Revert on bop000; confirm audible switching with Bob.
2. **Complete:** `patch-editor/pe-2-edit-mode` — single-instance GUI edit runtime, exclusive
   `off | simulate | edit` supervisor mode, patch list, live param panel, and
   explicit relaunch/restart behavior.
3. **Complete:** `patch-editor/pe-3-manifest-editor` — validated atomic param/cue editing and
   New patch flow using Bob's `main.pd` template verbatim when available.
4. **Complete:** `patch-editor/pe-3b-simulator-param-catchup` — bounded post-launch
   parameter replay fixes silent managed Pd starts caused by the initial gain
   catch-up arriving before the patch receive graph is ready.
5. **Complete:** `patch-editor/pe-4-points-and-cues-ui` — session-only point
   preview and cue firing through the normal `/pt` and `/cue` paths.
6. **Complete:** `pe-4b-editor-delivery-and-element-target` — align the live
   dashboard backend with PE-4 and add the element 0/1 editor point target.
7. `ui-tabs/tabs-0-ia-proposal` — short Overview / Spatial / Fleet management /
   Patch editor information architecture proposal.
8. Bob ratifies the tabs-0 information architecture.
9. `ui-tabs/tabs-1-skeleton` — implement the ratified tab structure without
   redesigning behavior.
10. `ui-tabs/tabs-2-review-session` — hands-on interactive UI/touch audit with
   Bob inside the real tabbed dashboard; split and complete any resulting
   fixes.
11. `patch-workflow-friction/friction-0-docs` — the simple composer workflow
   guide, written against the finished editor and tabs.
12. `patch-workflow-friction/friction-1-starter-kit` — finish the starter-kit
   path and teaching copy.

Other hardware and co-design waits remain outside this runway until explicitly
resumed.

## Source chain

- `.lore/items/2026-07-13-composer-experience-brain-dump/`
- `.notes/handoff-2026-07-13-dashboard-ui.md`
- `.notes/handoff-2026-07-14.md`
- `.notes/handoff-2026-07-14-fleetwide-patch-next.md`
- `.notes/handoff-2026-07-15-patch-editor-next.md`
- ratified fleet-patch and patch-editor records under `.lore/items/`
