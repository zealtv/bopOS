# PE-3 verification record

Verified 2026-07-15 on macOS in the project venv.

## Focused verification

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/patch-editor/pe-3-manifest-editor.stitching/verify_pe3_backend.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/patch-editor/pe-3-manifest-editor.stitching/verify_pe3_manifest_editor.py
```

- Backend and filesystem boundary: **12/12 passed**.
- Real dashboard + headless Chromium + no-engine audition relay: **12/12 passed**.

Together these prove validated atomic param/cue CRUD, read-only manifest fields,
live control refresh and OSC delivery without an engine restart, explicit PD
receive follow-up warnings, invalid-write byte preservation, symlink/path
containment, legacy string declaration handling, and duplicate/new-patch safety.

New Patch was exercised both ways. With Bob's source template at
`patches/.templates/bopos-template.pd`, the generated `main.pd` was byte-identical
and the minimal manifest was catalog-valid. With the temporary verifier copy
removed, New Patch succeeded manifest-only and the UI explicitly said that
`main.pd` was still required. The repository template was never modified.

Static Python compilation, JavaScript syntax, and `git diff --check` passed.
No tracked or untracked `.pd` diff was produced.

## Regressions

- `pe-1-contract-v1.4/verify_pe1_cues.py`: **10/10 passed**.
- `d8-4-sim-controls/verify_d8_sim_controls.py`: **9/9 passed**.
- `pe-2-edit-mode/verify_pe2_edit_mode.py`: **27/27 passed**, including the
  real GUI-PD launch and clean process teardown.
- `distribution-workflow/verify_distribution_ui.py`: **5/5 passed**.

Two older distribution artifacts were also run but are no longer clean as
whole suites: `dist-4-demos` timed out waiting for its historical seeded device
row after its first 12 checks passed, and `verify_distribution_workflow.py`
reported 7/9 because two copy assertions predate the fleet-patch UI. Neither
failure touches manifest editing or New Patch; current PE-3 distribution,
catalog, browser, and backend paths are covered by the focused suites above.

## Boundary

This stitch does not author Pure Data. It only copies Bob's supplied template
verbatim during New Patch. Interactive layout/touch judgement remains reserved
for `ui-tabs/tabs-2-review-session`.
