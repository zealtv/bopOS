# Proposal — node process ownership (67/19)

**Status:** proposal for Bob · no runtime code changed · 2026-10-05

## Summary (phone-length)

- Let systemd own every long-running node process: `bopos.service` (daemon),
  `bopos-io.service` (IO bridge), `bopos-engine.service` (JACK + engine
  instance), all grouped by one new `bopos.target`.
- Daemon and IO bridge become plain services with `Restart=always`. A crash
  now comes back on its own. Today it stays down until someone reboots (B4).
- Stopping uses systemd's cgroup kill. `stop.sh`, `stop-engine.sh`, the PID
  files and the name-wide `pkill` are all deleted (B5). D1's helper unit and
  `restart.sh` are deleted too.
- bopos.py still decides *when* the engine restarts, but it does it through
  `sudo systemctl start|stop|restart bopos-engine.service`. That needs three
  new exact-match sudoers lines.
- An invalid manifest only fails the engine unit. The daemon is a separate
  unit, so the node stays online without the 58/4 skip flag.
- Each existing Pi needs one `sudo bash/provision.sh` plus a reboot. A
  10-line `start.sh` shim keeps a dashboard-updated but unprovisioned Pi
  reachable until that's done.
- **Your calls:** the new sudo lines, the journal split, the migration shim,
  and leaving the engine on `Restart=no`.

## The model

**systemd owns processes; bopos.py owns engine policy.** Each long-running
process sits in exactly one unit's cgroup. systemd starts it, notices when it
dies, and kills everything in that cgroup when it stops. bopOS keeps no PID
records and never matches processes by name.

| Unit | Type | Runs | Restart | Notes |
|---|---|---|---|---|
| `bopos.target` *(new)* | target | — | — | `Wants=` the three services; the only enabled unit (`WantedBy=multi-user.target`). The operator's handle for the whole stack. |
| `bopos.service` *(rewritten)* | `simple` | `bash/start.sh daemon` → `python -u bopos.py 2>&1 \| logpipe run/bopos.log` | `always`, 2s, `StartLimitIntervalSec=0` | `PartOf=bopos.target`. `After=network-online.target`. Name kept so `systemctl status bopos.service` still means "the node daemon". |
| `bopos-io.service` *(new)* | `simple` | `bash/start.sh io` → `python -u io/main.py 2>&1 \| logpipe run/io.log` | `always`, 5s | `PartOf=bopos.target`, `After=bopos.service`. |
| `bopos-engine.service` *(new)* | `forking` | `bash/start-engine.sh` | **`no`** | `PartOf=bopos.target`, `After=bopos.service sound.target`. `RuntimeDirectory=bopos-engine`, `PIDFile=/run/bopos-engine/engine.pid`, `LimitRTPRIO=95`, `LimitMEMLOCK=infinity`, `TimeoutStartSec=120`, `TimeoutStopSec=15s`. |

All three services run as `User=pi`, `Group=pi`, `WorkingDirectory=/home/pi/bopOS`,
with `EnvironmentFile=-/etc/default/locale` and `KillMode=control-group` (the default).
Unit files stay root-owned in `/etc/systemd/system/`. They only run pi-owned
code as `pi`, so B1's trust boundary still holds.

### Why `Type=forking` for the engine

`start-engine.sh` already behaves like a forking daemon. It does the work
that can fail (manifest, run context, ALSA wait, JACK readiness,
`record-active`, survival check, patch `start.sh`), leaves JACK and the engine
instance running in the background, and exits. Its exit code is the launch
verdict (67/18). With `Type=forking`:

- `systemctl start bopos-engine.service` blocks until that script exits and
  returns its verdict. bopos.py's fetch, patch switch, audio apply/rollback
  and restart-engine paths keep the synchronous success signal they rely on.
- On a failed launch, systemd kills whatever the script left in the cgroup.
  That makes `cleanup_failed_launch` and `stop_failed_jack` redundant.
- `PIDFile=` names the engine instance as main process. If the engine dies,
  the unit stops and systemd kills JACK with it. Today JACK is left holding the
  card.

### How the engine fits bopos.py

| Today | Proposed |
|---|---|
| `run_command(["bash", stop-engine.sh])` | `sudo -n /usr/bin/systemctl stop bopos-engine.service` |
| `run_command(["bash", start-engine.sh], wait_for_start=True)` | `sudo -n /usr/bin/systemctl start bopos-engine.service` (blocks; same verdict) |
| `restart_engine_callback`: `Popen("stop && exec start")` | `sudo -n /usr/bin/systemctl --no-block restart bopos-engine.service` |
| `engine_alive()`: PID files + `process_is` + a **system-wide `comm` scan** | Unit is active **and** its cgroup holds a `jackd` and the manifest's engine process. Read from systemd's `ControlGroup` / `cgroup.procs`, so no subprocess per heartbeat. |
| `expected_engine_name()` reads `run/engine.name` | Reads the manifest (already its fallback) |

Engine `Restart=no` is deliberate. bopos.py already sequences
stop → change → start → roll back. If systemd retried on its own, it would
race that sequence, and an invalid patch would loop again (incident 211). An
engine crash is still *seen*: the unit goes inactive, JACK is freed, and the
heartbeat shows `engine 0`. It's *handled* the same way as today, by
restart-engine or a patch push. Automatic engine restart on crash
(`Restart=on-abnormal`) could follow later as a separate decision for you; I
don't recommend it in this stitch.

### Privilege

Add to `systemd/bopos-power.sudoers` (installed by `install-power-control.sh`,
which already validates the file):

```
/usr/bin/systemctl start bopos-engine.service, /usr/bin/systemctl stop bopos-engine.service, /usr/bin/systemctl restart bopos-engine.service, /usr/bin/systemctl --no-block restart bopos-engine.service
```

These are exact argument matches with no wildcards. They follow the existing
reboot/poweroff pattern. A polkit rule would avoid sudo, but it depends on
polkitd being on Lite images and would add a second authorization mechanism.
I'm not proposing it.

## What each script becomes

- **`bash/start.sh`** becomes a foreground service wrapper with two modes,
  `daemon` and `io`. It sources `bopos.config` for `IO_LOG_MAX_BYTES`, picks
  the venv Python, and runs one `python -u … 2>&1 | logpipe.py` pipeline under
  `set -o pipefail`. A dead service therefore exits non-zero and systemd
  restarts it, which fixes B4. Deleted from it: the background launches, PID
  writes, the ERR trap and its `stop.sh` call, `sleep 1`, the engine launch,
  and MAC discovery. bopos.py already resolves its uid from `state/uid`, then
  `discover_primary_mac()`.
  - *Per-boot work:* `start.sh daemon` deletes `run/audio-config.json` only
    if the file predates the current boot. A daemon crash-restart therefore
    can't erase a live engine's active-audio record, and a file the engine
    writes during this boot is never removed.
  - *Migration shim (temporary):* `start.sh` with **no argument** can only
    mean the legacy oneshot unit or `rc.local`. In that case it backgrounds
    `start.sh daemon`, logs `ERROR: unit model changed; run sudo
    bash/provision.sh and reboot`, and exits 0. It's deleted in a follow-up
    stitch once your hardware list is reprovisioned.
- **`bash/start-engine.sh`** is the engine unit's `ExecStart`. It writes
  `engine.pid` to `$RUNTIME_DIRECTORY` (`/run/bopos-engine`, tmpfs,
  removed when the unit stops) and keeps its survival check and exit codes.
  Deleted from it: `--skip-invalid-manifest` and its branch,
  `cleanup_failed_launch`, `stop_failed_jack`, and the `jackd.pid`, `pd.pid`
  and `engine.name` records.
- **`bash/provision.sh`** installs the four units and the updated sudoers
  file. It stops the old `bopos.service`, disables the old enablement, enables
  `bopos.target`, and says a reboot is required (it already asks for one). It
  keeps the legacy `rc.local` retirement as is.

## What gets deleted

| File / code | Why it goes |
|---|---|
| `systemd/bopos-helper.service` | D1. Unused, and it would duplicate the daemon. |
| `bash/restart.sh` | D1. Broad sudo, no callers. Replaced by `sudo systemctl restart bopos.target`. |
| `bash/stop.sh` | B5. PID-file and `pkill -f` stopping, replaced by `systemctl stop`. |
| `bash/stop-engine.sh` | B5. Trusts any live PID, and its fallback is a name-wide `pkill -x`. |
| `run/bopos.pid`, `io.pid`, `jackd.pid`, `pd.pid`, `engine.name` (and `run/engine.pid`) | No remaining reader. Today they survive across boots. |
| `start.sh` background/ERR-trap/MAC/engine code | Covered above. |
| `start-engine.sh` skip flag + partial-launch cleanup (~50 lines) | Unit isolation and cgroup kill now do this. |
| bopos.py `jack_alive`, `process_is`, `process_is_pd`, the `comm` scan, `run_command`'s start-engine special case | Replaced by the cgroup check and `systemctl`. |
| `test_manifest_boot.py` stop.sh fixture; PID assertions in it and `test_logpipe.py` | They test deleted mechanisms. |

That's 4 files deleted and 3 units added. Net, there's less shell and no PID
bookkeeping.

## Boot order

`multi-user.target` → `bopos.target`, which pulls in:

1. `bopos.service` after `network-online.target`. The daemon heartbeats and
   answers `/admin` before audio exists, as it does today.
2. `bopos-io.service` after the daemon is forked. That's the same order
   as today, minus the `sleep 1`.
3. `bopos-engine.service` after the daemon and `sound.target`. It waits up to
   60s for the ALSA card, as it does today.

`bopos.target` uses `Wants=`, never `Requires=`. A failed engine or IO unit
doesn't stop the target or the other units.

## Invalid-manifest connectivity (58/4)

This now comes from the structure. With an invalid manifest,
`start-engine.sh` exits 1, `bopos-engine.service` is *failed*, and nothing
retries it. The daemon and IO units are untouched. A pushed valid patch goes
through the existing fetch → `systemctl start` path and recovers without SSH.
58/4's "Must hold" items still hold. The `--skip-invalid-manifest` exception
disappears, because boot no longer needs one script to both stay up and
report failure.

## Upgrade and migration on existing Pis

A dashboard **Update bopOS** only does `git pull` and a reboot. It can't
install root-owned units, by design. So:

- **Per Pi, once:** SSH in, `git pull` (or update from the dashboard first),
  `sudo bash/provision.sh`, `sudo systemctl reboot`.
- **Updated but not yet provisioned:** the old oneshot unit runs `start.sh`
  with no argument. The shim keeps the daemon up, so the node stays reachable
  and heartbeats with `engine 0`, and the log says what to run. Engine control
  fails honestly because the new sudo lines aren't installed yet. Nothing
  loops.
- **Fresh installs:** `install-device.sh` → `provision.sh`. No change for the
  operator.
- **Rollback:** check out the previous commit, run `sudo bash/provision.sh`
  (the old one reinstalls the oneshot unit), and reboot. The leftover
  `bopos-io` and `bopos-engine` unit files are inert while
  `bopos.target` is disabled.

## Operator- and wire-visible changes (flagged)

**Wire: none intended.** The OSC contract, `/admin` replies and the
restart-engine verb are unchanged. One narrow semantic change is flagged:

- ⚑ **Heartbeat `engine` is stricter.** A `pd` (or other engine-named)
  process outside `bopos-engine.service` no longer reports `1`. Today the
  `comm` scan does count it.

**Operator-visible:**

- ⚑ **The stack is now four units.** Use `sudo systemctl restart|stop
  bopos.target` for everything, and `sudo systemctl restart
  bopos-engine.service` for audio only. `systemctl status bopos.service`
  shows only the daemon.
- ⚑ **Logs split.** Engine and JACK output goes to `journalctl -u
  bopos-engine` at boot *and* at runtime. Today runtime engine restarts write
  into `run/bopos.log`. `docs/INSTALL.md`'s `journalctl -u bopos.service`
  line becomes `journalctl -u 'bopos*' -b`. `run/bopos.log` and `run/io.log`
  stay where they are.
- ⚑ **Log rotation changes from per process start to per boot.** logpipe moves
  a log to `.prev` only if the log predates the current boot. Without this,
  two IO crash-restarts would overwrite the onset diagnostics the cap exists
  to keep.
- ⚑ **Daemon and IO now restart themselves.** A node that crashed used to stay
  dark until rebooted. Now it comes back within seconds. IO peripherals the
  patch created are gone after an IO restart, exactly as after today's manual
  restart. Re-creating them is a 59 question, not this stitch.
- ⚑ **The dev workflow changes.** "`bash/stop.sh` then `bash/start.sh` as
  pi" (glean `test-rig`) becomes `sudo systemctl restart bopos.target`, which
  needs sudo. Re-reading `bopos.config` becomes `sudo systemctl restart
  bopos-engine.service`, or restart-engine from the dashboard. Running
  `start-engine.sh` by hand outside the unit is unsupported. The glean finding
  is revised when this ties.
- ⚑ **New sudoers lines and a one-time reprovision**, as above.
- ⚑ **Performance mode.** Engine output now reaches journald at runtime too.
  Whether that writes the SD card depends on the image's journald storage.
  This is a Pi check. If it does write the SD, the engine unit gets
  `StandardOutput=null` while in Performance, which is a follow-on.

## Rejected alternative: keep the engine as a child of the daemon

The daemon would keep launching `start-engine.sh` itself, so JACK and the
engine would live in `bopos.service`'s cgroup. This needs no sudo and no
engine unit. I rejected it because:

- With `Restart=always` on the daemon, any daemon crash would kill audio
  mid-show. That's a regression, since today a daemon crash leaves audio
  playing. Avoiding it needs `KillMode=process`, which brings back unowned
  processes and PID files, the exact problem B5 describes.
- The engine still has no owner that can tell it apart from other processes.
  The success signal stays PID-file based.
- It doesn't survive the horizon refactor. `bopos-engine.service` becomes
  `bopos-engine@<instance>.service` almost unchanged when several engine
  instances arrive. JACK can split into its own unit then, with engines
  `BindsTo=` it. Neither change is proposed now.

## Test plan (fixtures; each fails before, passes after)

1. **B4 wrapper:** `start.sh daemon` with a fixture Python that exits 86
   returns 86, through pipefail. *Before:* `start.sh` returns 0.
2. **B4 unit shape:** a static parse of `systemd/*.service|target`.
   `bopos.service` and `bopos-io.service` are `simple`, `Restart=always`, no
   `RemainAfterExit`. The engine is `forking` with `PIDFile` under
   `RuntimeDirectory`, `Restart=no`, and `TimeoutStartSec` ≥ the ALSA + JACK
   + survival waits. The target `Wants=` all three and never `Requires=`.
   Every service is `PartOf=bopos.target`.
3. **B5:** no `bash/` script reads a `*.pid` to signal anything or calls
   `pkill`. The adapted `stale_pid()` reproduction has no stop script left
   to run. bopos.py's engine stop path sends exactly
   `sudo -n /usr/bin/systemctl stop bopos-engine.service` (mocked
   `run_command`).
4. **Heartbeat honesty:** `engine_alive()` against a fake cgroup tree. A stray
   `pd` outside the unit gives `0`. A `jackd` plus engine inside an active unit
   gives `1`. An engine without `jackd` gives `0`. *Before:* the stray `pd`
   gives `1`.
5. **Engine launcher:** the existing `EngineLaunchTests` cases, adapted. Every
   failure exits non-zero, the PID is written to `$RUNTIME_DIRECTORY`, and a
   successful launch exits 0. The partial-cleanup assertions move to the
   Pi checks, because cgroup kill does that work now.
6. **Invalid manifest:** `start-engine.sh` with a retired, missing or
   malformed manifest exits 1. There's no skip flag left, and test 2 shows
   no unit `Requires=` the engine. This replaces `test_manifest_boot`'s
   stay-online cases.
7. **Migration shim:** `start.sh` with no argument backgrounds the daemon
   fixture, prints the reprovision line and exits 0.
8. **Per-boot rotation and audio record:** with an injected boot time, logpipe
   rotates a log from an earlier boot but appends to one from this boot.
   `start.sh daemon` deletes an `audio-config.json` from an earlier boot and
   keeps one from this boot.
9. **D1 / deletions:** `bopos-helper.service`, `restart.sh`, `stop.sh` and
   `stop-engine.sh` are absent and nothing references them.
   `test_device_install` asserts the new provision lines and sudoers entries.
10. `tools/run-tests.sh` fast tier is green.

## Pi checks (Bob's hardware list; a separate claim)

On **bop000** first, then Ciro Toast (standalone) and Finn Jet (fleet):

1. Run `systemd-analyze verify` on the four units.
2. **Migration:** update from the dashboard *without* reprovisioning and
   reboot. The node stays reachable and the log names the fix. Then run
   provision and reboot. All three units are active, the uid is unchanged, and
   the heartbeat shows `engine 1`.
3. `kill -9` the daemon. It's back within ~2s and **audio keeps playing**.
   Do the same for IO.
4. `kill -9` pd. The unit goes inactive, `jackd` is gone, and the heartbeat
   shows `engine 0`. Restart-engine from the dashboard recovers it.
5. Patch switch. Fetch of the active patch. Audio-config apply, plus a forced
   rollback with an unsupported rate. Restart-engine.
6. Push an invalid manifest and reboot. The node is online and the engine unit
   is failed. Push a valid patch and it recovers without SSH.
7. Boot with the sound card absent. The node is online, and the engine fails
   after about 60s with no retry loop.
8. `sudo systemctl stop bopos.target` leaves no bopOS process in `ps`.
   `restart` brings it all back.
9. `jackd` keeps SCHED_FIFO 70 under the new unit (`chrt -p`), with no
   xrun regression.
10. Performance mode: check whether journald writes to the SD card (see above).
11. Dashboard reboot and poweroff still work.
