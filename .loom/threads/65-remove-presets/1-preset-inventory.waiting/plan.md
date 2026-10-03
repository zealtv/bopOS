# Remove presets completely

Inventory: 2026-10-03. This stitch changes planning artifacts only. The line-level
working-tree inventory is in `surface-audit.md`; it includes CSS, HTML, WebSocket
messages, Show schema and actual saved JSON, not just Python imports.

## Decisions and data

The replacement is ordinary live parameter control and literal Show messages;
there is no new snapshot facility, migration service or compatibility API.

Two operator-visible decisions are pending Bob's answers:

1. Proposed: reject a saved Show containing PRE/reference messages, report a
   clear unsupported-message error and preserve its bytes. Do not silently drop
   cues, emit `/preset/...` as raw OSC, or convert an invalid Show to an editable
   empty document. On an explicit load, validate before stopping transport or
   replacing the currently loaded Show. On startup, expose the failure and keep
   that file protected from autosave, editing, Save As and shutdown writes until
   a valid Show is explicitly selected or created. Use generic unsupported
   message validation rather than a special preset loader. Ordinary schema-1
   OSC shows remain valid; no version bump is needed for their unchanged shape.
2. Proposed: leave existing patch files untouched. Remove the special
   `presets/` distribution exclusion, making leftover files ordinary patch
   content: enumerated, fingerprinted, served and converged like other files.
   This changes the fingerprint of a patch with such files and may cause normal
   convergence/restart. It also removes the old prune exemption. No automatic
   deletion or move; an operator can archive unwanted files outside the patch.

Observed data:

- `dashboard/shows/test.json` contains two `/preset/bonks-pd/medium-bonks`
  reference messages at `items[11]` and `items[12]`. The file has user edits;
  do not rewrite, stage, delete cues or copy over it. Exercise the agreed stale
  behavior against a temporary copy instead. A clear refusal counts as clean
  handling, not as a successful load of unsupported content.
- `dashboard/installations/10x8-test.json` has an empty top-level `presets` key.
  Installation normalization already ignores it and durable save drops it;
  keep this generic unknown-field behavior. No bulk rewrite is needed.
- Venue read currently explicitly pops `presets`. Replace the ad hoc retired
  field special case with the existing supported-field projection on adoption
  and writing, ensuring old unknown fields cannot leak into public/durable data.
- Local untracked `patches/bonks-pd/presets/` has `medium-bonks.json`, `off.json`
  and `sparse.json`. There are no tracked patch preset files. They are Bob's
  authored content and this implementation must not delete them.
- Runtime `applied_preset`, `preset_dirty`, editor provenance and
  `preset_catalog` disappear. Durable Seat params, generator state, patch
  declarations, master, mute, spatial positions and assignments survive.

## Source surfaces: remove versus keep

| Surface | Removal and surviving responsibility |
| --- | --- |
| `dashboard/preset_store.py` | Delete the module: CRUD/CAS/cache, slug/file validation, drift resolution and schema projection/hash. The schema fingerprint has **no independent production consumer**: its only callers are preset catalogs and PRE reference warnings. Do not move unused scaffolding into manifest code. |
| `dashboard/preset_application.py` | Extract shared live control helpers to `dashboard/live_params.py`, then delete the old module. Keep `canonical_float`, `canonicalize_value`, `canonicalize_args`, `automation_key`, `automation_spec`, `automation_active`, `replay_args`, `estimate_automation` and the latter's `_shape`, `_fade_value`, `_random_value`, `_lfo_value` dependencies. Remove capture, target inference, provenance projection and dirtiness. |
| `dashboard/server.py` | Remove store initialization, PRE application queue/lock and methods, capture/save/delete, flattening, current-patch/schema reference fingerprint helpers, catalogs, dirty refresh calls and editor provenance projection. Remove preset permission/dispatch branches and all output messages. Retain `editor_target()` and `_editor_seat`: live editor automation uses them outside presets. Retain target selection, live declarations, replay, Stop estimation and editor parameter writes; retarget their imports to `live_params`. Remove `effective_patch_for_seat` if its last consumers vanish (current calls are preset-only). Preserve device-pin logic elsewhere for its own stitch. |
| `dashboard/osc_bridge.py` | Retarget shared automation helper imports; preserve takeover origins, held values, replay and timestamps. Reword reconnect comment that currently uses preset load as its example. |
| `dashboard/state.py` | Remove named runtime provenance filtering once no producer exists; retain an explicit supported-field durable projection so stale fields remain ignored. Retire venue's named `presets` pop as above. No change to Seat identity or parameter durability. |
| `dashboard/show_model.py` | Remove `reference` message kind, `clean_reference`, `preset_message_parts`, schema/content reference warnings and `flatten_preset_message`. No other production reference family exists. Keep schema, typed OSC args, steps/dividers, targets, group drift warnings, UIDs, duplicate/move/undo and persistence. Validate unsupported kinds at load; do not accept old pseudo-address messages as raw OSC. |
| `dashboard/show_engine.py` | Remove injected `apply_preset` and expansion path. Keep ordered message emission, OSC parameter/event dispatch and transport. Keep a generic fail-closed guard for unsupported message kinds even when called outside validated loaders. |
| `python/identity.py` | Remove `HOST_ONLY_DIRS`, `is_host_only` and their walk/cache gates: only presets use this policy. Preserve shared file ordering, SHA-256 content identity, hash cache, dotfile/symlink/`.part` exclusions. |
| `python/fetcher.py` | Remove host-only exemptions from prune, empty-directory cleanup and manifest acceptance. Preserve containment, symlink and hash safeguards. |
| `DistributionStaticFiles` in `dashboard/server.py` | Remove preset policy check and now-unused `patch_root` constructor/mount argument. Preserve generic dotfile, `.part` and symlink HTTP denial. |

WebSocket input types to delete: `apply_preset`, `preview_preset_capture`,
`save_patch_preset`, `delete_patch_preset`, `flatten_preset_message`.
Output types to delete: `preset_capture_preview`, `preset_saved`, `preset_applied`.
Remove their permission lists as well as dispatch and listeners. Other live
control/automation/Show edit messages keep their semantics.

## Browser, CSS and documents

- `control-surface.js`: delete preset menu/drawer/report/capture state,
  handlers, provenance rendering and exposed methods. Keep controls, generator
  drawers, input buffers and interaction guards; audit shared focus helpers
  before deleting anything just because a preset called it.
- `control-column.js`: remove preset callbacks, capability, report state,
  catalog projection, row insertion and report API. Keep card identity, target
  commands, replay and derived Remote membership.
- `control-host.js`: remove capability, callbacks and three WS listeners.
  `facilitator.js`: remove obsolete false capability and comments.
- `dashboard.js`: remove preset WS listeners, `presetContext`, pending preview
  and last report, editor/device rows and provenance members. Keep editor and
  device surface creation with their remaining callbacks. Update Seat
  reindex/delete confirmations that still promise preset handling. Restore a
  visible patch name in the Device panel header/context when removing the row
  that currently carries it; retain existing patch identity elsewhere.
- `show.js`: remove PRE category/pill, mode inference and builder option,
  picker, timed controls, reference creation/copying, flatten handler and
  catalog/content signature dependencies where unused. Keep parameter/event,
  point, raw OSC builders, targets, wire preview and current Show diagnostics.
- Delete `static/css/preset-menu.css`; remove its links from `index.html` and
  `facilitator.html`. Remove section 16 preset selectors in `control-panel.css`
  and preset pill rules/theme variables in `style.css`. Preserve spacing for
  controls now directly below headers, generic icon menus and generator CSS.
- Revise current instructions in `dashboard/README.md`, `docs/COMPOSING.md`,
  `docs/GETTING-STARTED.md` (including screenshot alt text) and
  `docs/VERIFICATION.md`. Visual inspection of `docs/images/tab-dashboard.png`
  confirmed an obsolete **SEAT PRESETS** shelf. Refresh affected current screenshots using an isolated
  fixture. Do not regenerate unrelated screenshots or tied evidence.
- Update current glean guidance if retirement makes it stale. Do not edit
  Lore or historical tied/dropped records, contract §15 history, or Pd files.
  No observed Pd change is required; if implementation discovers one, record
  it in `64-pd-edits-owed`.

## Contract amendment draft — not applied by this stitch

Replace §8.1 with:

> ### 8.1 Retired host-side facility
>
> Retired 2026-10-03 (v1.18). The former host-side saved-parameter facility is
> removed. Live controls and Show messages use ordinary §3.3 parameter traffic;
> no replacement storage format, reference message or wire verb is introduced.
>
> The v1.17 definition is historical; see §15.

Remove the §8 event capture sentence and §9 host-only directory bullet. All
ordinary directory rules remain. Preserve the existing v1.17 history entry.
Append to §15, update heading and `python/osc_contract.py` to 1.18 together:

> 1.18 | 2026-10-03 | Retire the host-side preset facility (§8.1), including
> patch storage APIs, capture/recall UI and Show PRE references. Remove §9's
> special distribution/fingerprint/prune/HTTP exclusion for `presets/`;
> leftover files follow ordinary patch rules. Existing installation/venue
> unknown fields are ignored. Unsupported saved Show message kinds are
> rejected visibly without rewriting source files. No wire grammar or node
> engine behavior is added. | `65-remove-presets` removal verification.

If Bob chooses different data handling, revise this draft before execution.
Bob has already requested this retirement; this inventory does not ratify a
new wire form or implement project design.

## Tests: delete only obsolete behavior; preserve shared coverage

Delete `test_preset_store.py`, `test_preset_menu.py`,
`verify_preset_control_surface.py`, `verify_preset_editor.py` once the feature
is actually removed. The first browser verifier is the current sole red
journey (24 pass, 1 fail baseline); do not skip or mask it ahead of removal.

Split surviving coverage out of `test_preset_application.py` before deleting:
replay/fade expiry, generator timestamps, Stop estimates, fade takeover origin
and Stop argument canonicalization must remain as live-control tests without
preset fixtures. Inspect inherited test methods in `PresetSurfaceServiceTests`
as well as explicitly named methods. Retain transport/rollback tests only for
remaining live-write responsibilities, not extinct batch-apply transactions.

Retire reference/drift/flatten tests in `test_show_model.py`; rewrite duplicate,
move, persistence, ordered playback and undo fixtures with literal messages.
In `verify_show_reference_foundation.py`, remove preset file/schema setup and
PRE authoring; retain named group targeting, missing-group warnings and
remaining literal Show editing, renaming the verifier to match its scope.

`verify_interaction_guard.py` must keep generator focus/heartbeat tests;
remove only preset drawer/capture sections. Revise the historical preset prose
in `test_dom_event_handlers.py` while preserving the delegated focus binding
checks. Remove preset requirements in `verify_control_tab.py`,
`verify_device_control_panel.py`, `test_cards_grid_css.py` and
`test_css_component_ownership.py`; replace them with meaningful surviving
control/card/patch-name assertions where appropriate.

Replace obsolete exemption tests in `test_identity_fingerprint.py`,
`test_fetcher.py` and the store's `DistributionDenyTests` with ordinary nested
content identity, distribution, convergence/prune and existing generic HTTP
denial checks. Preserve tests for genuinely hidden/control files.

Rename/reframe `test_venue_preset_retirement.py` as generic legacy unknown-field
handling; keep byte-preservation tests for rejected saved Shows, startup and
explicit load, and no pseudo-address transmission. Retirement regression
fixtures may spell old persisted fields/addresses: they are evidence of a
clean break, not surviving feature code. The removal acceptance grep therefore
allows these isolated stale-input fixtures as well as historical records.

## Execution order and acceptance

Keep `2-remove-presets` as **one coordinated change**. Shared module extraction,
server/UI removal and test retirement cannot each meet the green-tier contract
in isolation; adding child stitches would leave intentionally broken surfaces.
Its checklist is updated alongside this plan, not claimed by this inventory.

1. Settle the two data decisions above; preserve the user working tree.
2. Extract live helpers and coverage; remove host/schema/reference plumbing.
3. Remove browser/CSS/WS surfaces, preserving controls and patch context.
4. Apply agreed stale-data handling and ordinary distribution rules; verify
   against isolated fixtures, never rewrite Bob's current Show or patch files.
5. Apply contract 1.18 amendment and current docs/screenshots; migrate remaining
   tests and remove obsolete feature suites.
6. Audit tracked current files for `preset`, `PRE`, `/preset/`, old message
   types, imports and CSS names. Classify every residual match; history and
   narrowly scoped retirement fixtures only. Run `tools/run-tests.sh fast`
   and `browser`, record complete green summaries and screenshots in stitch 2.
7. Tie 2 only when green; the dependency then frees `5-browser-tier-red` for
   its own final gate confirmation. Commit using the installed fast hook.

Inventory verification: parsed every saved JSON under both specified folders,
enumerated local patch preset directories and tracked assets, traced shared
helper call sites and inspected validator/loader/dispatch/CSS/test consumers.
`tools/run-tests.sh fast` passed all 380 tests. No application change or browser
baseline rerun belongs to this planning stitch.
