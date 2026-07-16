# updatebopos-unattended results

## Software outcome

- `python/bopos.py` now owns runtime framework convergence in already-loaded,
  trusted code. A branch checkout cannot replace its update procedure
  mid-operation. Every external command runs in a new process group with a
  bounded timeout; timeout or cancellation sends TERM, escalates to KILL, and
  reaps the group before the admin lock is released. Python restores
  `patches/active_patch.txt` in `finally`, independently of shell traps.
- `bash/update.sh` is now the equivalent manual convergence-only script. It checks
  the existing narrow reboot authorization before touching Git, disables Git
  and SSH credential prompts, restores tracked changes, pulls fast-forward
  only, synchronizes submodules, and restores `patches/active_patch.txt` on
  both success and failure. It does not install root-owned files or reboot.
- `bash/provision.sh` owns the one-time privileged `rc.local`, ownership, and
  power-sudoers installation previously mixed into every update.
- Runtime convergence captures the result, sends an attributable
  `/os/rev ... <status> <phase>` receipt, and requests the already-authorized
  reboot only after `ok converged`. A rejected reboot sends `err reboot`.
- Checkout validates Git branch syntax, fetches an explicit remote-tracking
  refspec, proves that ref exists, pins the named local branch to it, and sets
  its upstream before submodule convergence. Branch syntax is rejected before
  tracked files are restored. Paths and missing remote branches fail as `err branch`.
  It sends only the checkout notification, not a duplicate update notification.
- The dashboard backend retains optional receipt status/phase, does not treat
  an error receipt as convergence, and shows the terse outcome on the existing
  selected-Device Converged line without adding help copy. Simfleet emits the
  successful update outcome for protocol parity.
- The optional receipt outcome is documented as an additive v1.6 extension.
  Legacy three-field receipts remain accepted.

## Verification

`PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python
.loom/threads/updatebopos-unattended.stitching/verify_updatebopos_unattended.py`
passed **50/50** checks. Controlled fake commands covered authorization, pull,
checkout-fetch and submodule boundaries; explicit remote/local branch proof;
path and missing-remote rejection; trusted-code continuity across checkout;
active-patch restoration; prompt-proof Git; receipt ordering; failure receipts;
and refused reboot. A deterministic hanging descendant test proved TERM/KILL
process-group cleanup, Python-side restoration, no late mutation, and admin-lock
release only after cleanup. The verifier also launched the real dashboard and
simfleet on loopback and observed two `updatebopos` receipts as `ok converged`
in dashboard device state.

Also passed:

- Bash syntax checks for update, checkout, provision, and power installer.
- Python compilation for bopos, dashboard OSC bridge, simfleet, and verifier.
- `git diff --check`.
- `.loom/tied/08-unbound-admin-seam/verify_uid_admin.py` passed its first
  **15** helper, routing and dashboard checks, then stopped at the removed
  pre-tabs `#unassigned` UI selector. Its next literal contract `1.5`
  expectation is also stale against current v1.6. This is historical UI/test
  drift rather than an updater failure; the new focused wire integration uses
  the current Devices model and `updatebopos` spelling.
- The helper-only portion of the old `os-admin-verbs` regression. Its old e2e
  portion still sends the retired `{"verb":"update"}` spelling and therefore
  receives no revisions; this is stale test input, not an `updatebopos` failure.
  The new focused wire check exercises the ratified spelling and passes.

## Remote/authentication audit

This checkout's framework origin is the public HTTPS URL
`https://github.com/zealtv/bopOS`; its `pd/bop` submodule is also public HTTPS,
so normal read convergence needs no stored GitHub credential. Runtime now sets
`GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`, Git's
`credential.interactive=never`, and SSH `BatchMode=yes`. If a deployed node has
been repointed to a private or inaccessible remote, update will honestly return
`err pull` rather than hang for credentials. Such a remote still needs a
pre-provisioned noninteractive credential helper or deploy key; this stitch
does not invent or distribute credentials.

## Remaining real-device gate

No real update, root-file installation, or reboot was run locally. On `bop000`,
Bob should trigger **Update bopOS** and confirm:

1. the helper journal records `status=ok phase=converged` with no prompt;
2. the node reboots only after that receipt;
3. it returns with the pulled short Git revision and the same active patch;
4. an intentionally unauthorized or unreachable test (only if Bob chooses to
   stage one safely) returns its phase and does not reboot.

The installed `/etc/sudoers.d/bopos-power` must already authorize exactly
`/usr/bin/systemctl reboot` and `poweroff`; missing authorization is reported as
`err authorization` and is repaired through the explicit privileged
`bash/provision.sh` path, not by broadening runtime sudo.
