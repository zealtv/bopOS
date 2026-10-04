# Install and services review addendum — 2026-10-05

Five repair findings: a root service executes a pi-writable helper; ignored
USB partitions can unmount the active stick; engine startup masks failures;
background node services are unsupervised; stale PID files can kill unrelated
processes. One small dead-code cleanup is also worth doing. No runtime code,
wire contract, lore items, or stitch lifecycle changed.

Reviewed `install-device.sh`, `install-dashboard.sh`, `run.sh`, all current
`bash/` lifecycle/provisioning scripts, and every `systemd/` file. The first
review's style and CONFIRMED/*likely* distinction are retained. The known
invalid-manifest/ERR-trap work in 58/4 is not duplicated here.

## Reproduction and verification

From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python .loom/threads/74-review-remaining/3-review-install-and-services.stitching/reproduce.py
```

`reproduction.log` records seven successful checks (three engine failure
cases, stale PID, USB ownership, background-service failure, privilege source
audit). The harness uses copied shell sources and temporary trees under
`/tmp`, inert JACK, failing engine/Python command stubs, and a mocked mounted
device. Its substitutions are documented in the script: ALSA path, USB
block-device predicate/path, and boot log redirection. It never runs sudo,
installers, real mounts, actual engines, or systemd. CONFIRMED below means
the specified software behavior, not a completed Pi hardware adoption.

Existing tests: `test_device_install.py` 6/6, `test_usb_automount.py` 8/8,
`test_manifest_boot.py` 3/3. Commands were venv Python with
`-m unittest discover -s tests -p '<module>.py'`, `TMPDIR=/tmp`, and
`PYTHONDONTWRITEBYTECODE=1`. The manifest boot module first failed because
the sandbox denied `/dev/fd/63` process redirection; its approved unsandboxed
rerun passed (`manifest-boot-unsandboxed.log`). Initial results are retained
in `verification.log`. Bash syntax checks passed for install/run scripts,
all `bash/*.sh`, `bash/bopos-usb-mount`, and `systemd/bopos-set-hostname`.
ShellCheck is absent. The full fast tier was not run: its commit-gate tests
execute `tools/install-hooks.sh` and make fixture commits, contrary to this
brief's no-installers/no-commits rules. No browser behavior changed.

## B1. USB service crosses the pi-to-root trust boundary

- **Severity:** High (local privilege escalation).
- **Location:** `systemd/bopos-usb@.service:16` and `:17`;
  `bash/provision.sh:27`; `bash/install-usb-automount.sh:29`.
- **Status:** **CONFIRMED source trust chain**, via
  `privilege_source_audit()` in `reproduce.py`. No root exploit was run.
- **Route:** repair child in `67-repair-pass`.

The system-level USB service has no `User=` and therefore runs as root. Both
commands execute `/home/pi/bopOS/bash/bopos-usb-mount`; provisioning explicitly
chowns the entire checkout to `pi`. A process running as `pi` can replace that
script (even chmod alone would not protect its writable parent directory),
then a USB add/remove or service stop executes the replacement as root.
This bypasses the otherwise narrow root-owned hostname/Wi-Fi helper design.
Private-LAN trust does not make the pi-owned executable root-owned.

Install the privileged mount helper into a root-owned directory outside the
checkout and point both unit commands there. Keep all imported/sourced code
and executable dependencies on that boundary root-owned. Test provenance and
reprovisioning with unprivileged fixture directories, then adopt on a Pi.

## B2. Removing an ignored USB partition unmounts the active stick

- **Severity:** Medium (logging interruption/data availability).
- **Location:** `bash/bopos-usb-mount:34`, `:71`;
  `systemd/bopos-usb@.service:8`, `:15`, `:17`.
- **Status:** **CONFIRMED** mocked command behavior, via `usb_ownership()`.
- **Route:** repair child in `67-repair-pass`.

When sda1 already owns the stable mount, mounting sdb1 returns success after
the already-mounted guard. The sdb1 oneshot unit therefore remains active.
Removing sdb1 stops its device-bound service and calls the same argument-less
`unmount`, which unconditionally unmounts sda1. An unsupported partition that
returns success can have the same stop consequence. Removal of another
partition on the same stick can also reach this ownership error.

Give each stop operation its instance identity and unmount only when that
instance owns the mount. Serialize competing add/remove operations too: the
current check-then-mount has no lock (*likely* concurrent-add race, not
reproduced). Test A mount, B ignore, B removal, A remains mounted; then A
removal. Rig yank/multi-partition behavior remains untested.

## B3. Engine-only launch reports success after required commands fail

- **Severity:** High (silent startup failure and unreliable audio rollback).
- **Location:** `bash/start-engine.sh:65`, `:141`, `:148`, `:153`, `:164`;
  related consumer `python/bopos.py:1241`.
- **Status:** **CONFIRMED**, via the three `engine_case()` checks.
- **Route:** repair child in `67-repair-pass`.

Unlike `start.sh`, `start-engine.sh` does not enable failure handling. A
runcontext command exiting 42 is wrapped by `eval "$(...)"`; eval of empty
output succeeds and fabricated fallback context is delivered. A failing
audio `record-active` command exiting 43 is ignored. A launched engine exiting
87 still produces PID files and launcher exit 0 when there is no patch
`start.sh` (the final `echo` succeeds). JACK can remain running after failure.
The harness confirms each case independently. It does not claim engine
readiness merely from successful process creation.

`_restart_audio_engine()` uses only the launcher exit code, so this directly
undermines audio-config apply/rollback. Fetch and patch-switch callers also
check `engine_alive()` and have additional protection; do not generalize the
failure to every caller.

Check required command results explicitly, including command substitution
before eval, and clean up only this launch's partial processes on failure.
Observe immediate engine death before reporting successful launch; preserve
the existing manifest-only skip exception for full-stack boot. Verify failing
context, failed active-audio recording, failed exec, failed patch hook, and
successful launch. This is post-validation launch handling, separate from
58/4's invalid-manifest boot gate.

## B4. Node and IO services can die while systemd reports a healthy boot

- **Severity:** High (node unreachable or sensors absent until intervention).
- **Location:** `bash/start.sh:71`, `:77`, `:81`, `:89`;
  `systemd/bopos.service:8`, `:19`, `:20`.
- **Status:** **CONFIRMED** immediate failure, via `boot_service_exit()`;
  later-crash recovery absent by source inspection.
- **Route:** repair child in `67-repair-pass` (structure may be a follow-on in 69).

Both Python commands run in the background, with no wait/check of their
status. The fixture proves that both can exit 86 while `start.sh` returns 0.
A one-second sleep does not turn background exits into an ERR trap failure.
When engine startup succeeds or its invalid-manifest skip applies, the
oneshot unit stays active because `RemainAfterExit=yes`; its
`Restart=on-failure` follows the oneshot launcher, not individual background
children. A daemon/IO crash does not trigger the declared restart policy.

Use one coherent ownership/supervision model that checks startup and handles
later service death. The unused helper unit is not currently a solution: it
would compete with start.sh for the same daemon. Preserve invalid-manifest
boot connectivity and partial-stack cleanup. Do not change operator wording
or the wire contract as part of the repair.

## B5. Stale PID files authorize killing an unrelated process

- **Severity:** Medium (unrelated process termination; possible root impact
  through the legacy restart wrapper).
- **Location:** `bash/stop-engine.sh:25`, `:28`, `:31`;
  `bash/stop.sh:13`; `bash/restart.sh:3`.
- **Status:** **CONFIRMED**, via `stale_pid()`.
- **Route:** repair child in `67-repair-pass`.

The stop scripts trust any numeric live PID in their files. No command,
start-time or process-ownership identity is checked; `engine.name` is only
used for messages. The fixture places an unrelated `sleep` PID with a
different recorded engine name in `engine.pid`; the actual copied stop script
kills it and returns success. PID reuse after an engine crash is a plausible
real trigger. `run/` persists PID files across boots, increasing stale-record
opportunities. The name-wide `pkill` fallback also exceeds ownership of one
launch. No real unrelated process was signalled in the reproduction.

Track and validate the launched process identity or delegate termination to
the owning supervisor/cgroup; keep fallbacks within owned processes. Test
stale/reused PID, corrupted PID input, ordinary stop and escalation after
timeout without killing arbitrary same-name processes.

## D1. Dormant helper service and privileged restart wrapper

- **Severity:** Low (cleanup/maintenance).
- **Location:** `systemd/bopos-helper.service:12`; `bash/restart.sh:3`.
- **Status:** *likely* unused externally; no in-repository caller or installer
  enables/copies the helper unit, and no runtime caller references restart.sh.
- **Route:** 70 dead-code, after the supervision repair chooses its model.

The helper unit duplicates a daemon already launched by start.sh and its
250ms unconditional restart policy would create a conflicting daemon if
enabled. The legacy restart wrapper still requires broad sudo to stop
processes that normally belong to pi, does not stop on failure, and was not
adopted by current Python lifecycle callers. Remove the unused files if the
chosen supervisor does not use them; check operator use before deleting the
wrapper. Do not install the current helper unchanged just to use it.

## Checked and dropped from proposed work

- `pi`, `/home/pi/bopOS`, and `/home/pi/venv` are deliberate documented device
  constraints; `install-device.sh` rejects other usernames. No portability
  repair proposed merely for these paths.
- Host installers and run.sh agree on `BOPOS_VENV`. Device config is preserved
  on reprovisioning; locale and package steps have explicit error behavior.
  The installer no longer performs an OS upgrade (67/9 already fixed it).
- Re-running initial provisioning deliberately reinstalls root-owned helpers;
  routine unprivileged convergence does not do that. Source inspection only:
  no installer was run and package availability on Pi OS releases was not tested.
- The hostname sudoers wildcard is bounded by the helper's one-argument
  lowercase hostname validation. Wi-Fi permits only empty arguments or
  `--status`, validates stdin, and imports the root-owned installed validator.
  Its unavailable backend is already tracked by 33b/2, not a new defect.
- `run.sh --host` can override the default bind address while the banner still
  lists LAN URLs, and existing-checkout install ignores BOPOS_BRANCH's clone
  override. These minor intent/wording ambiguities are dropped here; no new
  operator wording invented.
- No new 69 complexity stitch is justified independently of the concrete
  supervision repair. No Pi, USB, ALSA, JACK, Pd, reboot, distro/package or
  sudoers adoption claim is made.
