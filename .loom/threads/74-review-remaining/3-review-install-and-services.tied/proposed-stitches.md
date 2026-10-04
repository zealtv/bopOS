# Proposed stitches — review 74/3

These are proposals only; no stitch directories were created.

## Root-own the USB mount helper

- **Name:** `usb-helper-root-ownership`
- **Parent thread:** `67-repair-pass`
- **Goal:** make the privileged USB unit execute only helpers and dependencies
  installed outside pi-writable directories.
- **Done when:** both start and stop reference a root-owned installed helper;
  provisioning installs it idempotently without changing pi's runtime checkout
  ownership; fixture checks cover command provenance and replacement on
  reprovisioning; real Pi installation/USB adoption is recorded separately.

## Keep USB stops scoped to their owning partition

- **Name:** `usb-mount-instance-ownership`
- **Parent thread:** `67-repair-pass`
- **Goal:** an ignored USB device or partition cannot unmount the active stick,
  and competing mount operations have serialized ownership.
- **Done when:** A mount, B ignored add, B removal leaves A mounted; A removal
  unmounts A; unsupported partitions do not own the mount; concurrent add/stop
  fixture checks preserve one owner; multi-partition/yank rig checks are
  explicitly recorded as completed or pending.

## Make engine startup failures observable and clean

- **Name:** `engine-launch-failure-handling`
- **Parent thread:** `67-repair-pass`
- **Goal:** engine-only launch fails honestly when required context/audio
  recording/engine execution/patch hooks fail, and releases its partial stack.
- **Done when:** each failure has a nonzero result and no owned orphan JACK or
  engine; successful launch works; audio-config rollback observes failure;
  full-stack invalid-manifest skip remains available before audio starts;
  shell fixture tests cover these paths. Does not duplicate 58/4.

## Supervise the node and IO service lifetime

- **Name:** `device-runtime-supervision`
- **Parent thread:** `67-repair-pass`
- **Goal:** boot cannot report success after required Python services die, and
  later service death follows a deliberate recovery policy.
- **Done when:** one model owns all daemon/IO launches and stops; immediate
  command/import failures are detected; later daemon and IO exit recovers or
  enters an observable failure state; invalid-manifest boot keeps management
  reachable; partial failures do not duplicate processes or leak log sinks;
  software fixtures and real systemd adoption are separately recorded.

## Validate owned processes before stopping them

- **Name:** `stop-process-identity`
- **Parent thread:** `67-repair-pass`
- **Goal:** stale PID files and process-name fallbacks cannot terminate
  processes outside bopOS's owned launch.
- **Done when:** stale/reused/wrong-process and corrupted PID fixture cases
  leave unrelated processes alive; normal stop and bounded escalation work;
  node/IO/engine/JACK termination shares an explicit ownership rule. Coordinate
  with device-runtime-supervision to avoid parallel competing stop designs.

## Remove obsolete service and restart entry points

- **Name:** `obsolete-device-lifecycle-entrypoints`
- **Parent thread:** `70` (dead-code thread; steward chooses its canonical ID)
- **Goal:** remove the unused helper unit and legacy privileged restart wrapper
  if they have no role in the final supervision model.
- **Done when:** in-repo references and operator use are checked; unnecessary
  files and stale documentation are deleted; boot/update/restart use one
  consistent lifecycle path; software checks pass. Follow the supervision
  decision before deleting a unit it might legitimately replace.
