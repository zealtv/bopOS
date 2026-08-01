# Verification — 2026-07-07

Implementation drafted by codex-implement against `design-decisions.md`
(prompt/result copied here as `codex-prompt-2.md` / `codex-implement-result-2.md`),
then reviewed line-by-line against the design doc and contract §1/§2/§7/§11.
No protocol-fidelity corrections were needed this time. All checks below ran
on the laptop (Python 3.12, no smbus2, no pip).

## Static / review

- `bash -n` clean on all six scripts; `start-engine.sh`/`stop-engine.sh`
  executable.
- `start.sh` + `start-engine.sh` read line-by-line: jack args byte-identical
  to the old start.sh (`-P70 -p16 -t2000 -d alsa -dhw:$SOUNDCARD -p 512 -n 2
  -r 44100 -s -P`), PD `-send` line identical (`RANDOM/STARTTIME/STARTDATE/
  ACTIVEPATCH`), interactive waits guarded by `[ -t 0 ]` so headless boot
  still gets the full settle delays (read is skipped, sleep loop isn't).
- Pidfile capture is correct: io/main.py launched via `( cd … && exec … ) &`
  so `$!` is python, not the subshell.
- `helper.py`: `subprocess` already imported; `directory` in scope in
  `switch_patch_callback`; `bash -c '"$1" && exec "$2"'` argv indexing
  correct ($0 is the "restart-engine" label).

## Driven directly (pyOSC3 stub, `test_node_fixes.py` in session scratchpad)

- `sys_i2c` imports with no smbus2; `HAVE_SMBUS` False; `scan_bus() == []`.
- `have_bus(99)` False with no device node and no `BLINKA_MCP2221`;
  True with the env var set; `have_bus(1)` True where `/dev/i2c-1` exists.
- `/io/create` with no bus → `/io/error <name> no-bus` (contract §11 verbatim);
  unknown device type → `/io/error <name> create-failed`.
- `restart_engine_callback`: exactly one `subprocess.Popen`, detached
  (`start_new_session=True`), argv resolves to `bash/stop-engine.sh` then
  `bash/start-engine.sh`; reply `/restart-engine` sent to PD on 6661 first.
- The `bash -c` stop-then-start chain validated with real dummy scripts:
  stop ran, then start ran.

## Simfleet live (loopback UDP, python-osc from scratchpad wheel)

- 2 devices, `dashsim.py send all helper restart-engine` →
  `/rpt <id> helper-reply restart-engine` from both devices exactly 0.5 s
  after the command, heartbeats undisturbed.

## Not verified (needs hardware / Bob)

- **Not hardware-verified**: real-Pi boot via rc.local, jackd/pd pidfile kill
  on a live engine, actual `/os/restart-engine` round trip through PD (needs
  the PD route edit in `../pd-edits-for-bob.md` §1), MCP2221A laptop
  peripheral create. Reply-before-kill has a theoretical race (PD must
  forward the reply before stop-engine's kill lands) — expected fine in
  practice (UDP forward is sub-ms, Popen+bash spawn is tens of ms), but only
  a live rig proves it.
