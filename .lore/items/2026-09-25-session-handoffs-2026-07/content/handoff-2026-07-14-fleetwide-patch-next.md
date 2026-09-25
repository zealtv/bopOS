# Handoff — patch distribution, device lifecycle, and fleet-wide patch next step (2026-07-14)

State at handoff: patch distribution and switching now work in the managed
simulated fleet and on bop000. Real-device patch switching is engine-only,
waits for a usable JACK server, and has passed an audible demo-pd/bonks-pd
hardware gate. Dashboard reboot works end to end again; shutdown has the same
verified authorization but was not executed because bop000 cannot be powered
back on remotely. No loom stitch is claimed. Local `main` and `origin/main`
both point to `a714920`.

## Start the next session here

Bob wants to begin by considering the technical and UI/UX implications of a
single fleet-wide patch assumption for both simulation and deployed devices.
Do not begin by implementing per-device patch selection. First produce a
compact model/proposal covering:

1. How one fleet-level desired patch simplifies the technical dashboard and
   facilitator UI.
2. How it simplifies dashboard state, distribution, simulation, engine
   lifecycle, parameter schemas, and convergence.
3. How bopOS distinguishes a device running the wrong patch from one running
   the right patch name but stale/different patch content.
4. How fleet desired state and per-device observed state appear in the sidebar
   without turning every device card back into a patch-management interface.

The likely simple UI shape to evaluate is one fleet patch selector/status in a
global control area, with device rows carrying compact observed-state badges:
`current`, `switching`, `missing`, `mismatch`, `unknown/offline`, and perhaps
`stale`. Per-device patch dropdowns and Send Patch controls can disappear from
the ordinary interface. Device detail can retain diagnostics and remediation,
but it should not imply that heterogeneous patches are a supported composition
model yet.

## Important identity distinction

Patch name is not sufficient to detect drift.

- The existing `/os/patches` response can identify the active patch by name
  and whether each installed patch is git-managed and has a valid manifest.
  The dashboard already refreshes `/os/patches`, `/os/params`, and `/os/report`
  after `/os/rev`, so wrong-name detection can build on the current convergence
  path without putting patch state in PD.
- `/os/rev` currently reports the bopOS framework revision, not the active
  patch's content identity.
- Two devices may both report `bonks-pd` while containing different commits or
  different host-mirrored files. Reliable `stale` detection therefore needs a
  separate patch identity: for example an immutable deployment/content digest,
  or a patch revision recorded when distribution lands. Git SHA alone covers
  git-managed patches but not host-mirrored patches.
- The next design should define one fleet `desired_patch` plus desired content
  identity, and compare it with each node's last observed active patch identity.
  Offline must remain `unknown/last seen`, not be treated as current or mismatched.

Prefer adding observed patch identity to an existing framework-owned report or
patch inventory response over increasing heartbeat payload unless there is a
clear convergence/latency reason. Any wire addition must remain additive to the
ratified v1.3 contract and be mirrored in simfleet and managed audition.

## Simplifications worth testing in the proposal

- One durable desired patch in installation state instead of per-device patch
  choices.
- One manifest/parameter schema for the fleet; the global/facilitator controls
  no longer need to reconcile incompatible per-device parameters.
- One simulated fleet patch selection and one managed audition engine family.
- Distribution becomes stage once, fan out, observe convergence, retry only
  missing/stale nodes.
- Patch switching becomes one fleet operation with per-device progress rather
  than N independent authoring choices.
- Sidebar rows become health/convergence summaries; exceptional rows draw
  attention without duplicating the global selector.
- Heterogeneous patches remain an explicit future architecture bridge, not
  latent complexity in today's state model or UI.

Open design questions: whether fleet desired patch persists in
`installation.json`; what exact digest/revision is portable across git-managed
and mirrored patches; whether switching is all-at-once or staged; rollback
semantics when only part of a fleet converges; and what actions an operator gets
from a mismatch badge (`retry`, `inspect`, or both).

## Work completed this session

### Distribution and patch switching

- `e436a06` / tie `c65c5a0`: simulated distribution is host-backed; all valid
  host patches appear; simulation uses one fleet-wide patch; Simulate no longer
  exposes a misleading Send/Sync path; real LAN source URL derivation works
  when the dashboard browser is on localhost.
- `7cea5eb` / tie `9a660ae`: `/os/patch` now stops and restarts only the audio
  engine stack, preserves the device/helper, validates launch, refreshes patch,
  params and report state, and rolls back the selection on failure.
- `4b8d549` / tie `795998b`: live bop000 gate proved demo-pd switching without
  a device reboot and with parameter refresh.

### JACK lifecycle correction

- Reproduced the silent bonks failure: old JACK took about 24 seconds to
  release, replacement JACK logged `Failed to open server`, the launcher slept
  five seconds and started PD anyway, and PD-only health made the UI converge.
- `a62ced4` / tie `d37fd29`: stop waits and escalates boundedly; start requires
  tracked JACK readiness via no-autostart `jack_lsp`; failed launches do not
  start PD; heartbeat engine health requires JACK and the selected engine.
- Focused verifier 7/7 and existing patch-switch verifier 10/10 passed.
- Live demo-pd -> bonks-pd switch passed. Bob confirmed bonks audio and Identify
  after the final switch.

### Device power controls

- Root cause: bopOS moved to unprivileged user `pi`, but callbacks still called
  systemd directly from a background rc.local session. Polkit recorded
  `Interactive authentication required`.
- `07da6b1` / tie `a714920`: the helper uses non-interactive sudo for exactly
  `/usr/bin/systemctl reboot` and `/usr/bin/systemctl poweroff`; a root-owned
  `0440` sudoers rule grants only those commands.
- Fresh Pi provisioning installs and validates the rule automatically through
  the documented `sudo bash/update.sh` path. Existing installs have a one-time
  authenticated migration; later updates detect and reuse installed auth.
- Focused verifier 9/9 passed. A targeted `/0/os/reboot` message rebooted bop000
  end to end; it returned with helper, verified JACK, bonks-pd, and both hardware
  outputs. Shutdown authorization was verified but poweroff was not executed.

## Current bop000 state

- Repository filesystem revision: `a714920`.
- Active patch: `bonks-pd`.
- Boot path remains `/etc/rc.local` -> `su pi -c /home/pi/bopOS/bash/start.sh`.
- The installed but disabled `bopos-helper.service` is not supervising the node.
- The last observed boot had a healthy helper, JACK, PD, and JACK playback graph.
- `/etc/sudoers.d/bopos-power` is root-owned, mode `0440`, and full sudoers
  validation passed.

## Known edges not to lose

- `verify_dist2_node_side.py` has one stale simulator-only assertion requesting
  active patch `default`, while the current simulated fleet starts on
  `demo-pd`; all real-node distribution checks passed.
- The unprivileged `/os/updatebopos` path still contains legacy privileged
  `sudo cp rc.local` behavior. Fresh root-run provisioning is correct, and the
  power-rule installer is idempotent, but framework-update lifecycle deserves a
  separate audit rather than broadening the power sudo rule.
- Boot journals still show several unrelated sudo password warnings during PD
  startup. They predate the new power callback and were not diagnosed in this
  session; do not mistake them for reboot authorization failure.
- No `.pd` file was edited.

## Loom and verification state

- No stitch claimed; 78 tied, 5 dropped.
- Next listed loose ends remain `patch-workflow-friction/friction-0-docs` and
  `friction-1-starter-kit`, but Bob's explicit next-session priority is the
  fleet-wide patch model/design above. Create and claim a focused stitch for it
  before implementation.
- Local worktree was clean at handoff before this handoff note was added.
