# rev-outcome-receipts

Bob (2026-07-17): fix the receipt gap the OSC-reference cross-check found
(`.loom/tied/4-osc-quickref/notes.md`). Five provisioning verbs —
`addpatch`, `pullpatch`, `droppatch`, `dropassets`, `patch` (switch) —
always send a **bare** `/os/rev <sha> <model> <uid>` with no status/phase,
even on failure or refusal, so an operator with a bare OSC client cannot
tell success from failure.

## Design (pinned)

- Make `add_patch_callback`, `pull_active_patch_callback`,
  `drop_patch_callback`, `drop_assets_callback`, and
  `switch_patch_callback` in `python/bopos.py` return small outcome dicts
  the way `converge_framework` already does, so `run_admin_verb` /
  `rev_reply` append `<status> <phase>` to the existing optional bracket.
  No contract amendment needed — `[<status> <phase>]` is already optional
  in v1.7; this is the code catching up to the bracket.
- `status` is `ok` or `err`. Pick short, terse phase words consistent with
  the existing converge phases (read `converge_framework` first); every
  early-return failure path gets a distinct phase (e.g. `invalid-name`,
  `not-found`, `active-patch`, `clone-failed`, `stopped`, `switched`,
  `restore-failed` — choose from what the code actually distinguishes,
  don't invent states the code can't observe).
- Mind existing callers of the callbacks' return values: the engine `/admin`
  path (`ENGINE_ADMIN_VERBS`) and `switch_patch_callback`'s internal
  True/False returns — grep every call site and keep truthiness-based logic
  working (a dict with status "ok" is truthy; failures previously returned
  None/False, so return the dict AND check whether any caller branches on
  the return; adjust callers to interpret the dict, never the other way).
- `pull_active_patch_callback` runs a script that ends in reboot — send the
  receipt BEFORE the reboot can land where achievable, mirroring the
  unattended-update receipt-before-reboot pattern; if the script's reboot
  makes ordering unachievable without restructuring, record that honestly
  in notes.md instead of pretending.
- Update `docs/OSC-REFERENCE.md`'s note under the lifecycle/provisioning
  table: these verbs now return status/phase; keep one sentence saying
  older nodes may still send bare receipts.
- `tools/simfleet.py`: if it fakes any of these five verbs' `/os/rev`
  replies, mirror the status/phase there; if it doesn't model them, say so
  in notes.md.

## Verification

`verify_*.py` in this stitch directory, browser-free, run with
`~/.venvs/bopos/bin/python`: exercise the callbacks directly with
monkeypatched subprocess/filesystem effects (nothing may clone, reboot, or
rm -rf outside a temp dir) and assert each failure path yields
`err <phase>` and each success `ok <phase>` through `run_admin_verb`'s
reply (fake reply socket capturing the datagram). Repo located by marker,
never fixed `..` hops. Also re-run the tied
`.loom/tied/2-engine-admin-requests/verify_*.py` as a regression gate.
