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

## Fresh-device gate — in progress on `new-bop`

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
launcher and unit now address both conditions. Hardware retest is pending.

Do not tie this stitch until the corrected revision is reachable from the raw
GitHub URL and the fresh Raspberry Pi has passed the remaining checks:

1. Flash Raspberry Pi OS Lite 64-bit with user `pi`, Wi-Fi, and SSH.
2. Run the README `curl .../install-device.sh | bash` command.
3. Confirm `~/bopOS/bopos.config` contains `SOUNDCARD=DigiAMP` and
   `MIXER_CONTROL=Digital`.
4. Confirm `locale` reports `LANG=en_AU.UTF-8` without warnings and
   `/etc/default/locale` contains no `LC_ALL`.
5. Reboot, then capture:
   - `systemctl status bopos.service --no-pager`
   - `journalctl -u bopos.service -b --no-pager`
   - `cat /proc/asound/cards`
   - `pgrep -alf 'bopos.py|io/main.py|jackd|pd'`
6. Confirm the device appears in the Dashboard and its engine is alive.
7. Exercise device mute/resume and confirm JACK/PD remain running.
8. Rerun `install-device.sh`; confirm it fast-forwards cleanly, preserves a
   harmless marker/comment added to `bopos.config`, and leaves one boot stack.
9. Run `shellcheck install-device.sh bash/provision.sh bash/start.sh
   bash/start-engine.sh` and, if available,
   `systemd-analyze verify /etc/systemd/system/bopos.service`.

Hardware, boot timing, audio, systemd, and end-to-end idempotence remain
unverified until that gate.
