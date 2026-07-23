# Verification

## Local checks

- `bash -n install-dashboard.sh install-device.sh bash/provision.sh
  bash/start.sh bash/start-engine.sh` — pass.
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python
  tests/test_device_install.py` — 6 tests pass.
- `./install-dashboard.sh --help` and `./install-device.sh --help` — pass.
- `git diff --check` — pass.
- `shellcheck` is not installed on the development Mac; run it on the device or
  install it before tying.

The living test checks explicit installer entry points, the raw-GitHub command,
composition through provisioning, locale generation without global `LC_ALL`,
config preservation, systemd lifecycle hooks, and the cold-audio readiness
guard. It also fixes the fresh-Pi regression checks for headless JACK device
reservation, systemd's realtime/memory-lock limits, and the terminal automatic
reboot.

## Fresh-device gate — pass on `new-bop`

The 2026-07-23 raw-GitHub run completed on a freshly flashed Raspberry Pi OS
Lite device. Package installation, locale generation, recursive clone,
configuration seeding, sudoers validation, service enablement, and
`systemd-analyze verify` passed. After reboot, a fresh login reported
`LANG=en_AU.UTF-8` with no warning. The full-card root partition was already
expanded before install (7.4 GiB card, 6.9 GiB partition); ext4 exposed 6.8 GiB
after filesystem metadata.

The first cold boot exposed a headless-JACK failure before PD could start:
the DigiAMP was present and unclaimed, but JACK tried D-Bus device reservation
without a display. Diagnostics also confirmed that the system service had
`LimitMEMLOCK=8M` / `LimitRTPRIO=0`, unlike the `audio` user's PAM limits. The
launcher and unit now address both conditions.

The corrected `fa7bd53` revision then passed two unattended boots. On each,
`bopos.service` was active with `Result=success`, `NRestarts=0`, unlimited
memlock, and realtime priority 95. bopOS, the I/O bridge, JACK, Pure Data, and
`pd-watchdog` were running; JACK exposed DigiAMP playback and Pure Data ports;
the expected 6660/6661/6662/8880 UDP listeners were present.

The public one-liner was rerun at `fa7bd53`. Apt, device packages, Python
dependencies, Git, and submodules were already converged; the existing venv was
reused. It preserved the config exactly (SHA-256 remained
`6dede45e538540fac125aebd83d2378e098a09291bfb6941a89a596f08e1905c`) and
triggered its own reboot. The stack returned active with zero service restarts.

The final exact-UID mute lifecycle also passed. Resume changed both DigiAMP
`Digital` channels to `[on]`; mute restored them to `[off]`. JACK and Pure Data
retained their PIDs throughout and the service remained active. The Dashboard
host's installation state contained this UID as `Finn Jet`, bound to seat 0,
and was updated while the node was online.

`systemd-analyze verify` passed on the Pi. `shellcheck` was unavailable on both
the development Mac and the fresh Pi; bash parsing plus the living installer
test are the recorded static checks.

The boot journal also exposed a separate legacy assignment bug:
`set_hostname()` tries three interactive sudo commands to rename `new-bop` to
the invalid hostname `Seat 0`. Those commands fail harmlessly and the service
continues. This belongs to the identity/alias path and is recorded in the
fresh-install lore report rather than folded into the installer.
