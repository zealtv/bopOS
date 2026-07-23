# Fresh bopOS device installation — 2026-07-23

## Purpose

This is the first monitored end-to-end run of the GitHub-centric
`install-device.sh` created by loom stitch `31-install-oneliner /
1-install-script`. The test used a freshly flashed, live Raspberry Pi and the
same raw-GitHub command intended for operators.

## Device baseline

- Host: `new-bop`
- Address during the run: `192.168.0.102`
- User: `pi`
- Architecture: `aarch64`
- OS before package upgrade: Debian 13.5 (Trixie)
- Kernel: `6.18.34+rpt-rpi-v8`
- Audio:
  - `DigiAMP` — RPi DigiAMP+
  - `vc4hdmi`
- `~/bopOS`: absent
- `bopos.service`: absent
- User groups included `sudo`, `audio`, `i2c`, and `gpio`

The fresh login had a locale warning because `LC_CTYPE=en_AU.UTF-8` referred to
a locale that was not generated. `LANG` was `en_GB.UTF-8`; the only available
locales were `C`, `C.utf8`, `en_GB.utf8`, and `POSIX`.

Storage was already expanded across the card before installation:

- `/dev/mmcblk0`: 7.4 GiB
- boot partition: 512 MiB
- root partition: 6.9 GiB
- ext4 root filesystem: 6.8 GiB usable
- before install: 2.3 GiB used, 4.2 GiB free

The apparent difference between the 6.9 GiB partition and 6.8 GiB filesystem is
normal ext4 metadata overhead, not an unexpanded filesystem.

## Command

```sh
curl -fsSL https://raw.githubusercontent.com/zealtv/bopOS/main/install-device.sh | env LANG=C LC_ALL=C bash
```

The raw URL was fetched from the Pi before the run, confirming that the public
GitHub delivery path was live.

## Installation run

The initial command installed commit `0dbf2c7`.

Successful phases:

1. Validated sudo access.
2. Asked `raspi-config` to expand the root filesystem and enable I2C.
3. Updated the package indexes and upgraded Raspberry Pi OS from Debian 13.5 to
   13.6.
4. Installed ALSA, JACK, Pure Data, Git, Python venv/pip, I2C tools, and locale
   support.
5. Generated and selected `en_AU.UTF-8`.
6. Recursively cloned bopOS and its nested submodules.
7. Created `/home/pi/venv`.
8. Installed the device Python requirements.
9. Installed the narrow power-control sudoers policy after validating the full
   sudoers configuration.
10. Seeded `/home/pi/bopOS/bopos.config`.
11. Installed and enabled `bopos.service`.

Notable non-failures:

- Apt reported transient `Packages.diff/Index` size mismatches, then correctly
  fell back to complete package indexes.
- Pip experienced one transient PyPI disconnect and succeeded on retry.
- `raspi-config do_expand_rootfs` printed a verbose fdisk exchange, but the root
  partition already ended at the card boundary and its geometry did not change.

The package upgrade changed 59 packages and downloaded about 104 MB. Device
dependencies added 183 packages, downloaded about 135 MB, and consumed about
554 MB. Much of that footprint came from Debian's `puredata` meta-package
pulling graphical/Qt dependencies; a future lean headless package selection is
worth investigating separately.

The recursive clone transferred approximately:

- bopOS: 18.26 MB
- `pd/bop` submodule: 4.71 MB at `e4f171…`
- nested bop sample pack: 29.78 MB at `1aecb50…`

Post-install disk usage:

- bopOS checkout: 110 MB
- Python venv: 26 MB
- root filesystem: 3.3 GiB used, 3.2 GiB free (51%)

## Installed configuration

The new config contained:

```ini
SOUNDCARD=DigiAMP
MIXER_CONTROL=Digital
HB_TARGET=255.255.255.255
HB_RSSI=1
UPDATE_MODEL=persistent
AUDIO_CHANNELS=2
```

The checkout was clean at `0dbf2c7`. The service was enabled, and
`systemd-analyze verify` returned no findings.

## Locale result

Before reboot, `/etc/default/locale` contained only:

```ini
LANG=en_AU.UTF-8
```

The original SSH shell still carried its pre-install environment, so it was not
a valid proof of the new login default. After reboot, a fresh SSH login emitted
no locale warning and reported:

- `LANG=en_AU.UTF-8`
- every ordinary `LC_*` category resolved to `en_AU.UTF-8`
- `LC_ALL` was unset

This confirms that generating the locale under `LANG=C LC_ALL=C`, then setting
`LANG` without a global `LC_ALL`, handles a fresh AU installation cleanly.

## First cold-boot finding

The first enabled-service boot exposed a real headless audio failure. The
service retried every five seconds and its cleanup correctly removed each
partial bopOS/I/O/JACK stack, so no duplicate processes accumulated.

JACK failed with:

```text
Failed to connect to session bus for device reservation
To bypass device reservation via session bus, set JACK_NO_AUDIO_RESERVATION=1
Audio device hw:DigiAMP cannot be acquired
```

It also warned that it could not lock about 38.7 MB of memory.

Diagnostics established:

- the DigiAMP was present;
- no other process owned any `/dev/snd` device;
- no PipeWire, PulseAudio, WirePlumber, or JACK process held the card;
- login sessions for the `audio` group received `memlock=unlimited` and
  `rtprio=95` from `/etc/security/limits.d/audio.conf`;
- the systemd service instead had `LimitMEMLOCK=8M` and `LimitRTPRIO=0`.

The failure was therefore caused by JACK's desktop-oriented D-Bus reservation
path in a headless service, with a separate systemd/PAM limits mismatch.

## Correction

Commit `26a2467` made two focused changes:

- `start-engine.sh` defaults `JACK_NO_AUDIO_RESERVATION=1`, while preserving an
  explicit caller override;
- `bopos.service` sets `LimitMEMLOCK=infinity` and `LimitRTPRIO=95`, matching the
  JACK limits already granted to login members of the `audio` group.

After pulling that commit and reprovisioning, the live service passed:

- `bopos.service`: active
- bopOS Python process: running
- I/O bridge: running
- JACK: running against `hw:DigiAMP`
- Pure Data and `pd-watchdog`: running
- JACK ports: two system playback ports and Pure Data input/output ports
- service limits: unlimited memlock, realtime priority 95

Commit `fa7bd53` then changed successful `install-device.sh` completion to print
a disconnect warning and call `sudo systemctl reboot` automatically. The
documentation and living installer test were updated to match.

## Final cold-boot result

The Pi rebooted onto `fa7bd53` and passed the unattended cold-start gate:

- fresh login had no locale warning;
- checkout was clean at `fa7bd53`;
- `bopos.service` was enabled and active;
- service result was `success` with zero restarts;
- service limits were unlimited memlock and realtime priority 95;
- bopOS, the I/O bridge, JACK, Pure Data, and `pd-watchdog` were all running;
- JACK exposed the two DigiAMP playback ports and Pure Data input/output ports;
- UDP listeners were present on 6660, 6661, 6662, and loopback 8880.

The published one-liner was then run a second time. Apt had nothing to upgrade,
all device packages and Python dependencies were already satisfied, Git and
submodules were already current, the existing venv was reused, and provisioning
reported that it preserved the existing device configuration. The installer
printed its completion/disconnect notice and rebooted the Pi automatically.

After that installer-triggered reboot:

- the config SHA-256 was still
  `6dede45e538540fac125aebd83d2378e098a09291bfb6941a89a596f08e1905c`,
  exactly matching the pre-rerun hash;
- checkout remained clean at `fa7bd53`;
- the service again reported `success`, active, with zero restarts;
- bopOS, I/O, JACK, Pure Data, and `pd-watchdog` were all running;
- JACK ports and AU locale remained correct.

This passes the install, automatic reboot, cold-start, and idempotent-rerun
portions of the fresh-device gate.

The node's persistent device-mute intent was enabled at the start of the final
check. An exact-UID OSC resume changed both DigiAMP `Digital` playback channels
from `[off]` to `[on]`; restoring mute changed both back to `[off]`. JACK and
Pure Data retained the same PIDs through both transitions, and the systemd
service remained active. The original muted state was therefore restored.

The dashboard host had already registered this UID as `Finn Jet`, bound to seat
0, and its installation state was updated while this final Pi was online. This
was sufficient for the installer gate; no visual browser walkthrough was part
of this report.

## Unrelated legacy warning observed

The successful boot journal contains three non-fatal sudo authentication
warnings. They come from the legacy assignment loader attempting:

```text
Hostname change: new-bop -> Seat 0
```

Its old `set_hostname()` path runs three unrestricted interactive `sudo`
commands and also treats the seat label—with a space—as an OS hostname. All
three operations fail, after which the node continues normally as `new-bop`.
The newer exact-UID alias-derived hostname helper is already a separate,
provisioned path. This should be retired or reconciled in its owning
identity/alias work rather than hidden inside the installer stitch.

## Follow-up observations

- Consider replacing the Debian `puredata` meta-package with the smallest
  supported headless package set in a separate optimization stitch.
- Retire the legacy CSV assignment-time `set_hostname()` calls in favour of the
  validated alias-derived hostname helper.
- The installer is intentionally GitHub-centric for now. A separate script host
  remains deferred.
- USB auto-mount remains deferred to stitch 35.
