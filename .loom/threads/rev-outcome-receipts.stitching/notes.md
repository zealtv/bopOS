# rev-outcome-receipts — notes

Fixes the gap `.loom/tied/4-osc-quickref/notes.md` found: `addpatch`,
`pullpatch`, `droppatch`, `dropassets`, and `patch` (switch) in
`python/bopos.py` always sent a bare `/os/rev <sha> <model> <uid>`, even on
refusal or failure, so an operator with a bare OSC client could not tell
success from failure. No contract amendment needed — `[<status> <phase>]`
was already optional (v1.6); this is the code catching up to the bracket.

## What changed

- `switch_patch_callback`, `add_patch_callback`, `pull_active_patch_callback`,
  `drop_patch_callback`, and `drop_assets_callback` in `python/bopos.py` now
  return `{"status": "ok"|"err", "phase": "..."}` dicts on every path,
  mirroring `converge_framework`'s existing shape. `run_admin_verb`/
  `rev_reply` already handled dict outcomes (built for `converge_framework`),
  so no change was needed there.
- `bash/pull_active_patch.sh` no longer ends with a bare `reboot`. The
  script now only pulls and reports its exit code; `pull_active_patch_
  callback` maps that exit code to a phase and returns `{"reboot": True}`
  on success, so `run_admin_verb` sends the `/os/rev` receipt *before*
  requesting the reboot — the same receipt-before-reboot ordering
  `converge_framework`/`update_bopos_callback` already use. This was a real
  restructuring (the design doc allowed recording "unachievable" instead,
  but the fix turned out to be a one-line script trim plus reusing the
  existing `run_admin_verb` reboot-request path, not a redesign, so I did
  it rather than punting).
- `tools/simfleet.py`'s `admin_verb` fakes all five verbs' `/os/rev`
  replies (via `send_rev`); it now mirrors status/phase for each, using the
  same phase words as `python/bopos.py` where the sim can distinguish the
  same states, and a smaller set where it can't (the sim doesn't model a
  disk that fails to write, so there's no `write-failed`/`remove-failed`/
  `stop-failed`/`start-failed`/`restore-failed`/`clone-failed`/`not-found`-
  from-network equivalent — those phases only exist in the real node).
- `docs/OSC-REFERENCE.md`: the lifecycle/provisioning table, the `/os/rev`
  summary row, the worked `patch` example, and the "Verified against"
  closing note all now say these five verbs set status/phase, and name the
  phase vocabulary. Added one sentence: older nodes running a framework
  build from before this revision may still reply bare for these five
  verbs — a bare reply from one of them means an old node, not a refusal.

## Phase vocabulary chosen (per verb)

- **`patch` (switch_patch_callback):** `invalid-name`, `not-found`,
  `stop-failed`, `write-failed`, `start-failed`, `restore-failed`; success
  `ok switched`. `start-failed` vs `restore-failed` distinguishes "the new
  patch failed to start but the old one was restored" from "the new patch
  failed to start AND there was nothing to restore to" (no prior active
  patch) — both are real, distinct states the code observes.
- **`addpatch` (add_patch_callback):** `invalid-args` (fewer than 2 args),
  `invalid-name` (bad user/repo pattern), `not-found` (remote `ls-remote`
  failed or errored), `remove-failed` (couldn't clear an existing folder of
  the same name), `clone-failed` (clone failed or timed out); success
  `ok cloned`. A cloned-but-manifestless patch is still `ok cloned` — the
  operation (clone) succeeded; the manifest warning is a separate, existing
  concern logged to stdout, not a receipt failure.
- **`pullpatch` (pull_active_patch_callback):** maps
  `bash/pull_active_patch.sh` exit codes 1→`active-patch`, 2→`not-found`,
  3→`not-found`, 4→`pull-failed`; any other nonzero code (defensive) also
  falls back to `pull-failed`; a `subprocess.TimeoutExpired` is `timeout`;
  any other exception is `exception`; success `ok pulled`.
- **`droppatch` (drop_patch_callback):** `invalid-name`, `active-patch`
  (refusing to remove the currently active patch), `remove-failed`
  (`OSError` during removal); success `ok dropped`.
- **`dropassets` (drop_assets_callback):** `invalid-name`, `remove-failed`;
  success `ok dropped`.

`invalid-name` is reused across verbs for "the identifier itself is
malformed/missing" rather than inventing a separate word per verb, since
that is genuinely the same class of failure everywhere it appears.

## Caller/return-value audit

Grepped every call site of the five callbacks (`grep -rn` across the repo,
not just `python/bopos.py`). Only `PROVISION_VERBS`/`ENGINE_ADMIN_VERBS`
(both routed exclusively through `run_admin_verb`, which already treats a
dict outcome specially and falls back to a bare `rev_reply` for any
non-dict return) call these functions in the shipping code path.
`switch_patch_callback` previously returned bare `True`/`False`;
`run_admin_verb` never branched on that boolean itself (it only checks
`isinstance(outcome, dict)`), so switching to a dict return is safe there.

Several **historical, already-tied** verify scripts do call these
callbacks directly and assert on the old `True`/`False`/`None` return
shape: `.loom/tied/patch-switch-lifecycle/verify_patch_switch_lifecycle.py`
(asserts `result is True`/`result is False`) and (more loosely)
`.loom/tied/dist-2-node-side/verify_dist2_node_side.py` and
`.loom/tied/patch-manifest/test_patch_manifest.py` (call the callbacks but
don't assert on the return value). Per CLAUDE.md, tied stitch directories
are historical artifacts, not a standing regression suite; the instructions
named exactly one regression gate to re-run
(`.loom/tied/2-engine-admin-requests/verify_*.py`, 15/15 here) and I did
not touch other tied directories. Flagging this here for visibility: if
`patch-switch-lifecycle`'s verify script is ever re-run standalone, its two
`result is True`/`result is False` assertions will now fail against a dict
return; that script was not re-run or edited as part of this stitch.

## Ambiguities resolved (smallest reasonable choice)

- The instructions allowed "record it honestly in notes.md" if the
  reboot-before-receipt ordering was unachievable without restructuring
  `pull_active_patch.sh`. It needed restructuring (the script's own
  trailing `reboot` made true ordering impossible), but the restructuring
  turned out to be small (delete one line from the script, add a `reboot:
  True` flag the existing `run_admin_verb` reboot path already knows how
  to use) — well within "smallest reasonable choice", not a redesign, so I
  did it instead of recording it as a gap.
- `add_patch_callback`'s existing "cloned but manifest invalid" warning
  path was not given its own phase (see above) — treated as `ok cloned`
  since the clone itself is what the phase reports on.
- `pull_active_patch_callback`'s exit codes 2 and 3 (no `.git` repo found;
  `cd` into the patch dir failed) both map to `not-found` rather than
  inventing a second phase for the (very unlikely) race where the
  directory disappears between the `.git` check and `cd` — the code can't
  actually distinguish why the directory became unreachable.

## Verification

`verify_rev_outcome_receipts.py` in this stitch directory (browser-free,
run with `~/.venvs/bopos/bin/python`) — **50/50 checks pass** (see
`verify_run.log`). Structure:

- Fakes `pyOSC3.OSCServer`/`OSCClient` before `import bopos`, mirroring
  `.loom/tied/2-engine-admin-requests/verify_*.py`, so importing `bopos`
  never binds the real UDP ports and never fights a running instance.
- A `Sandbox` context manager points `bopos.BOPOS_DIR` at a fresh
  `tempfile.mkdtemp()` per test group and stubs `run_command`,
  `engine_alive`, `hb_wake`, and `request_power_action`; `subprocess.run`
  and `shutil.rmtree` are saved/restored explicitly (both are the *same*
  module objects `bopos.py` imported, so patching `bopos.subprocess.run`
  patches the real global `subprocess.run` — Sandbox restores the real
  functions on exit rather than pretending a separate `bopos.subprocess`
  attribute swap would isolate it).
- Exercises every failure and success phase for all five callbacks
  directly (no real git clone, no real reboot, no real `rm -rf` outside
  the temp dir — `os.chmod` is used once, on a directory inside the temp
  dir, to force a real `PermissionError` for the `write-failed` case, and
  is always restored in a `finally`; skipped automatically if running as
  root, where permission bits don't apply).
- A dedicated `receipt_before_reboot_check()` drives
  `pull_active_patch_callback` through `run_admin_verb` with a fake reply
  socket and a fake `request_power_action` that both append to one
  ordered event list, and asserts the receipt event precedes the
  reboot-request event.
- `run_admin_verb_rev_reply_checks()` confirms the dict-outcome →
  `/os/rev <status> <phase>` wiring end-to-end (including the
  callback-raised-an-exception → `err exception` path), decoding the
  captured datagram with the real `pyOSC3.decodeOSC`.
- `simfleet_mirror_checks()` drives `simfleet.SimFleet.admin_verb`
  directly (with `schedule` executing immediately) and asserts its
  `send_rev` status/phase for all five verbs.

Also re-ran `.loom/tied/2-engine-admin-requests/verify_*.py`
(the named regression gate) — **15/15 pass**, unaffected.

Not independently verified: real-hardware behaviour (an actual failed
`git clone`, an actual permission-denied filesystem, an actual reboot).
That needs a live Pi or `bop000`; the monkeypatched paths above exercise
the exact same Python code the hardware would run, just with the
network/filesystem/power side effects substituted.
