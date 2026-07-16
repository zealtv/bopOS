# Handoff — aliases complete; unattended updater at hardware gate (2026-07-16)

This supersedes `.notes/handoff-2026-07-16-device-alias-design-ratified.md`.

## Completed in software

- Physical-device aliases now have a global durable registry, deterministic
  `Freda Sparks`-toned generator, Rename/Reset, genuine Forget, and alias-only
  everyday display. Hostname and full UID/MAC appear only in selected Device
  detail.
- Final integration added late-discovery registry convergence and 44 px alias
  controls. Focused browser verification passes 18/18; vocabulary 9/9;
  identity guard 6/6; registry 16/16; Seats 12/12; Assets 17/17; Dashboard
  parameters 12 checks with no failures.
- The older alias verifiers' UID-tail/`Identity.full` assertions and the old
  Devices suite's literal contract `1.5` assertion are superseded historical
  expectations. The older UID-admin browser regression likewise passes its
  helper/routing checks before stopping on the removed pre-tabs `#unassigned`
  selector (and would next expect contract `1.5`); tied evidence was not edited.
- Runtime `Update bopOS` no longer performs privileged provisioning or prompts.
  `bash/provision.sh` owns first-time root setup. Update/checkout preserve the
  active patch, disable credential prompts, fail with attributable phases, and
  reboot only after a successful receipt. The existing selected-Device
  Converged line shows the terse outcome. Focused verification passes 50/50.

## Gates and next actions

1. Commit and deploy the updater repair, then perform a Bob-triggered real
   `bop000` update. Confirm `ok converged`, reboot, returned short revision and
   unchanged active patch. The updater stitch remains waiting until this gate.
2. Bob must ratify or revise
   `.loom/threads/ui-tabs/tabs-3-next-sweep/12-dashboard-live-controls.waiting/device-mute-contract-proposal.md`
   before individual physical-device mute implementation. The proposal adds an
   exact-UID full-state mute with acknowledgement, persistent device mute, and
   the existing fleet safety mute as a session OR overlay.
3. Live parameter targeting and per-Seat/All **Send all** need no contract
   amendment and may proceed after the gate/decision sequencing is settled.
4. The diagnostic-density pass also owns Seats inspector dividers, a
   non-destructive two-element UI authoring cap, and bound-device IP display in
   the Physical device section. It must not expose hostname or UID there.

Seat/Group mute and solo remain deferred. No `.pd` files changed. No real Pi,
root installation, reboot, Safari/iPad, screen reader or audible behavior was
tested in this software pass.

The manually started dashboard process that was present during this session
predates the backend changes; restart it before judging late-discovery or
update-receipt behavior.
