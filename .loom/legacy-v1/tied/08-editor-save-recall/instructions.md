# 08-editor-save-recall

Preset save/recall in the **patch editor** — the primary sculpt→save
workflow, which the shared-`ControlSurface` row does not cover. **Needs 06
tied.** Parallel with 07.

Authority: proposal §7, first review U5 (the editor is a separate
`editorParamTree` implementation with no preset row or generator drawer —
`dashboard/static/js/dashboard.js:1035-1067`), addendum §10.6 ("the proposal
under-budgeted it").

## Scope

- The editor's control panel gains the preset row for **the patch being
  edited**: list, apply (recall), `new`/`save`/`del`, following the same
  ratified row anatomy as 07 so the two surfaces read as one language.
- **Save captures seat 0** — the audition engine the editor drives, the same
  selector `set_editor_param` writes to. Include/exclude per row, as in 07.
- **Recall applies through the 06 core** to seat 0 (one application path,
  R1) so clamping, canonicalization, report, and provenance behave
  identically to the Control tab.
- Saving writes through the 05 store (atomic, revision token) into
  `patches/<patch>/presets/` — the same host-side pathing that writes
  `bopos.patch.json`. Because `presets/` is fingerprint-excluded (05), a
  save while sculpting must **not** mark the fleet patch stale or trigger
  any restage — assert this in a test; it is the workflow the whole
  exclusion exists for.
- Drift is unlikely mid-edit but not impossible (manifest edited between
  save and recall); the row's inline drift/dirty treatment carries over.

## Out of scope

Generator drawer for the editor tree (not part of this thread), Show
integration, Control-tab surfaces.

## Verify and tie

Headless editor flows work with `--sim-no-engine` (and
`--sim-audio-backend none`) — `set_edit` reaches real `supervisor.mode`
without Pure Data; see `tests/verify_device_control_modes.py` as the
template. Cover: save from editor captures seat-0 state (value + running
generator args); recall restores after a nudge; save does not change the
patch fingerprint / staleness; delete. Real PD/GUI behaviour remains a
hardware adoption check — say so in the tie note rather than claiming it
verified. `tools/run-tests.sh browser` and `fast` green.
