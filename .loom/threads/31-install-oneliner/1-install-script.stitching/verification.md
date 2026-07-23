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
guard.

## Fresh-device gate — pending Bob

Do not tie this stitch until the raw GitHub script is reachable from the revision
being tested and a fresh Raspberry Pi has passed:

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
