# bopOS running order — quick reference

Last reconciled: 2026-07-16 against the live Loom and Bob's accepted next
seven-stage sweep.

This is the human-readable priority runway. `./.loom/loom.sh status` remains
authoritative for claims and live stitch state; `CLAUDE.md` remains authoritative
for repository rules. Work one stitch at a time using claim → work → tie.

## Current position

The foundation, dashboard IA/review, patch editor, fleet patch workflow, and
next-sweep stitches through Devices and Patches are tied. The parameter-address
foundation is also tied: nested manifest identity, relay, simulator, dashboard
state/presets/catch-up, and editor path CRUD are verified. The complete
Seat-group spatial UX is ratified and tied. There is no active claim; Seat-group
core and Assets 11a are the two loose ends, with Seat-group core first.

## Running order

1. **Complete: Parameter-address foundation** — true nested OSC, flat
   compatibility, canonical dashboard state, and editor authoring are tied.
2. **Complete: Seat-group spatial UX gate** — the rail visualization,
   eye/eye-off convention, authoring model, and subordinate Groups hierarchy
   are ratified and tied.
3. **Next: Seat-group core** — protocol, persistence,
   matching, simulator/audition behavior, dashboard state, and synchronization.
4. **Seat-group delivery** — implement group authoring and the ratified spatial
   visualization.
5. **Assets 11a then 11b** — observed per-device inventory followed by the
   single-device Assets workspace; fleet-wide asset rollout remains a separate
   parked thread.
6. **Dashboard live controls** — the sole All / Group / Seat integration point
   for flat and nested promoted parameters.
7. **Finish and document** — diagnostic density, device-alias design gate, then
   patch-workflow-friction docs and starter kit.

Other hardware and co-design waits remain outside this runway until explicitly
resumed. In particular, the 2026-07-15 sequencer brainstorm is unratified input
to `scene-sequencing`, not an implementation instruction and not part of this
sweep. `framework-version-management` also remains parked.

## Source chain

- `.lore/items/2026-07-13-composer-experience-brain-dump/`
- `.notes/handoff-2026-07-13-dashboard-ui.md`
- `.notes/handoff-2026-07-14.md`
- `.notes/handoff-2026-07-14-fleetwide-patch-next.md`
- `.notes/handoff-2026-07-15-patch-editor-next.md`
- `.notes/handoff-2026-07-16-seven-stage-sweep.md`
- `.loom/tied/param-address-0-design/proposal.md`
- `.loom/tied/seat-groups-0-design/proposal.md`
- ratified fleet-patch and patch-editor records under `.lore/items/`
