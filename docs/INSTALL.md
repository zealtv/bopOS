# Installing a node

How to take a Raspberry Pi from blank SD card to a fleet member, and how to
set up the network that the fleet and dashboard share. One node takes about
half an hour, most of it unattended.

> **Honesty note:** these steps describe the supported path on real
> hardware. Steps marked *(bench-verified)* have been run on a real Pi;
> anything else you should expect to confirm on your own bench, and
> [HARDWARE.md](HARDWARE.md) is the procedure for bringing up an audio
> board bopOS hasn't met before.

## What you need

- Raspberry Pi running **Raspberry Pi OS Lite (64-bit)** — the Pi Zero 2 W
  is the supported floor
- an audio output ALSA/JACK can drive, e.g. an IQaudio DigiAMP+ (the
  benched reference — see the board table in [HARDWARE.md](HARDWARE.md))
- a Wi-Fi network shared with the dashboard machine (next section)
- optional I2C peripherals: sensors, buttons, ADCs, touch, displays

The stock image and scripts assume the `pi` user and `/home/pi/bopOS`. The
wire protocol itself doesn't care about the username, the board, or even
that it's a Pi.

## The venue network

bopOS needs one thing from the network: the dashboard machine and every
node on the same LAN, with UDP broadcast allowed (ports
[5550 and 6660](PORTS.md)). Venue and house networks routinely break this —
client isolation, broadcast filtering, captive portals — so the reliable
pattern is to **bring your own router**.

The travel-router checklist:

- [ ] Bring a small dedicated travel router. It needs no internet uplink to
      run a show — the fleet is fully self-contained.
- [ ] Give it a standing SSID and password of your own, identical across
      your rigs and recorded in the venue kit, so every flashed node joins
      without re-imaging. Treat the pair as part of the installation — the
      SSID baked into your SD cards is the one the router must broadcast.
- [ ] Disable AP/client isolation if the router has it (nodes and dashboard
      must see each other's UDP).
- [ ] Leave DHCP on — bopOS identifies nodes by their stable `uid`, never
      by IP, so lease churn is harmless.
- [ ] Flash every node with this SSID as its installation Wi-Fi (step 1
      below). At the venue: power the router, power the Pis, open the
      dashboard. Nodes appear from their heartbeats.
- [ ] For internet-dependent steps (first clone, Git patch pulls), either
      give the travel router a temporary uplink or do those steps at home.

## 1. Flash the SD card

Use Raspberry Pi Imager with **Raspberry Pi OS Lite (64-bit)**. In the
Imager's settings:

1. create the `pi` user and a password;
2. configure the installation Wi-Fi (your travel-router SSID);
3. enable SSH.

## 2. Install the device

SSH into the freshly flashed Pi as `pi`, then paste this one command:

```sh
curl -fsSL https://raw.githubusercontent.com/zealtv/bopOS/main/install-device.sh | env LANG=C LC_ALL=C bash
```

The script is served directly from the bopOS GitHub repository for now. It asks
for sudo authentication, prepares Raspberry Pi OS, clones or fast-forwards the
checkout, installs the Python environment, creates `bopos.config` if it is
absent, enables `bopos.service`, and reboots after a successful run. The SSH
session will disconnect at that point. It is safe to rerun: existing device
config is preserved, and an existing checkout is only fast-forwarded.

The default system locale is `en_AU.UTF-8`. To choose another UTF-8 locale:

```sh
curl -fsSL https://raw.githubusercontent.com/zealtv/bopOS/main/install-device.sh |
  env LANG=C LC_ALL=C BOPOS_LOCALE=en_GB.UTF-8 bash
```

The installer generates the locale, sets `LANG`, and removes stale global
`LC_ALL`/`LANGUAGE` overrides that otherwise produce warnings or confuse Python
package installation.

The installed defaults target a DigiAMP+. After the Pi returns, adjust them if
this device uses a different audio board, then reboot again:

```sh
nano ~/bopOS/bopos.config
sudo systemctl reboot
```

After reboot, inspect the service with:

```sh
systemctl status bopos.service
journalctl -u bopos.service -b
```

Continue at [Point it at the audio board](#4-point-it-at-the-audio-board).

## 3. Manual installation fallback

The one-liner above automates the following steps. Keep this path for
troubleshooting, offline preparation, and reviewing exactly what changes.

### Prepare the system

Boot the Pi and log in (`ssh pi@raspberrypi.local`), then:

```sh
sudo raspi-config nonint do_expand_rootfs
sudo raspi-config nonint do_i2c 0
sudo env LANG=C LC_ALL=C apt-get update
sudo env LANG=C LC_ALL=C DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
echo "jackd2 jackd/tweak_rt_limits boolean true" | sudo debconf-set-selections
sudo env LANG=C LC_ALL=C DEBIAN_FRONTEND=noninteractive apt-get install -y \
  alsa-utils jackd2 puredata git python3-pip python3-venv i2c-tools locales \
  build-essential python3-dev swig
sudo env LANG=C LC_ALL=C DEBIAN_FRONTEND=noninteractive apt-get install -y \
  liblgpio-dev   # optional; absent before Bookworm
sudo raspi-config nonint do_change_locale en_AU.UTF-8
sudo update-locale LANG=en_AU.UTF-8 LC_ALL LANGUAGE
```

### Install bopOS

```sh
python3 -m venv ~/venv
git clone --recursive https://github.com/zealtv/bopOS.git ~/bopOS
~/venv/bin/pip install -r ~/bopOS/python/requirements.txt
cd ~/bopOS
sudo ./bash/provision.sh
```

`provision.sh` is the **one-time privileged step**. It installs the boot
service, the validated hostname helper, the initial device config, narrow
sudoers rules that let the unprivileged node software reboot, power off, or
apply a hostname — and nothing else — and the USB auto-mount udev rule +
mount unit (a stick is mounted at the stable path `/media/bopos-usb` so the
node logging facility can write to it). Everything after this runs as `pi`;
the mount itself needs no privilege at runtime.

> Existing fleet Pis that predate the hostname helper or the USB auto-mount
> need one manual `sudo bash/provision.sh` after updating; the routine
> **Update bopOS** action deliberately cannot install root-owned pieces.
> `provision.sh` is idempotent — a re-run installs only the missing pieces.

### If the pip step fails to build `lgpio`

`failed to build installable wheels for some pyproject.toml based projects
-> lgpio` means pip had to compile `lgpio` and could not.

`lgpio` is not a direct bopOS dependency. It arrives through
`adafruit-blinka`, which the `adafruit-circuitpython-*` requirements pull in;
`RPi.GPIO` and `rpi_ws281x` come the same way. All three sit behind Raspberry
Pi platform markers, so they appear only when resolving **on** a Pi.

`lgpio` publishes aarch64 wheels for cp39–cp312 only, and piwheels builds
armhf only — so on a 64-bit image running Python 3.13 (Trixie) pip has to
compile it, and that build needs **swig**.

Install the packages listed under [Prepare the system](#prepare-the-system)
— `build-essential python3-dev swig`, plus `liblgpio-dev` where available —
and rerun the pip line. The one-liner installs these itself; a Pi provisioned
before that change needs them added by hand.

> Measured on Trixie 64-bit Lite, Python 3.13.5, 2026-08-10: `build-essential`
> and `python3-dev` were already installed and `swig` was not, so `swig` +
> `liblgpio-dev` were the whole fix. `RPi.GPIO` 0.7.1 compiled without
> complaint on 3.13 — the `rpi-lgpio` shim is not needed.

## 4. Point it at the audio board

JACK opens the ALSA card named by `SOUNDCARD`; installation defaults to the
verified DigiAMP+ pairing in `bopos.config`:

```sh
SOUNDCARD=DigiAMP
MIXER_CONTROL=Digital
JACK_SAMPLE_RATE=44100
JACK_PERIOD_SIZE=512
JACK_NPERIODS=2
```

Check what your board is called and edit those values if it differs:

```sh
cat /proc/asound/cards
nano ~/bopOS/bopos.config
```

Once the node is online, the Dashboard's Device → Audio section can select
among playback cards ALSA currently detects and apply these JACK settings with
a transactional engine restart. Driver/overlay installation remains a manual
provisioning and reboot task.

A board bopOS hasn't been benched on must be checked for playback **and**
engine-safe mute before you trust it in a show — follow the bench procedure
in [HARDWARE.md](HARDWARE.md) and add your row to its table.

If you're using I2C peripherals, confirm the bus sees them:

```sh
i2cdetect -y 1
```

## 5. First contact

Reboot the device. On the dashboard machine (see
[Getting started](GETTING-STARTED.md) for setup):

```sh
~/.venvs/bopos/bin/python dashboard/server.py --host 0.0.0.0
```

The new node appears in the **Devices** tab within seconds, unassigned and
announcing itself quickly. Use **Identify** to make the physical box reveal
itself, bind it to a Seat, and drag its elements into place on the **Seats**
map. The assignment persists on the node — from now on it survives reboots
and runs with no dashboard present.

## Updating a node

Routine updates are driven from the dashboard (**Update bopOS**, per device
or fleet-wide). The node's already-running software performs the
convergence itself: restores and pulls the checkout, preserves the active
patch selection, updates submodules, reports its outcome receipt, and only
reboots after success. Failures fail loudly with the phase that failed —
never a silent half-update. `bash/update.sh` on the node is the equivalent
manual check and never reboots.

Two rules follow from this design:

- **Don't keep uncommitted work on an installation node.** Convergence
  restores the checkout.
- **Privileged changes need a person.** Anything touching root-owned
  configuration (like the sudoers policy) means one manual
  `sudo bash/provision.sh` per node.

## Python dependency pins

`dashboard/requirements.txt`, `python/requirements.txt` (nodes), and
`python/requirements-laptop.txt` all load the root `constraints.txt`.
`requirements-dev.txt` adds pinned Playwright, Pillow and pyflakes to the
complete dashboard/software-test environment. CI uses the dev file too.

The Python 3.10+ dashboard/test constraints preserve the working host venv's
2026-10-03 versions. Python 3.9 uses a separate, compatible set selected by
markers; the newer packages do not support that floor. Both sets include
transitive dependencies for macOS/Linux. Node sensor libraries and optional
laptop adapters were resolved in scratch venvs because the working dashboard
venv did not contain them. The laptop requirements use `piicodev`, which
supplies the `PiicoDev_SSD1306` module; that module name is not a separate
package requirement.

**Rig versions are unchecked.** These are software-tested Python pins, not a
claim that Finn Jet or Ciro Toast currently runs them or that the sensor/audio
hardware has been tested with them. The earlier Trixie 64-bit Lite/Python 3.13.5
build observation above is historical; the current Pi OS image, Python, Pd and
JACK package versions on both devices remain unchecked. Apt packages are not
locked by these Python constraints. `install-device.sh` still runs its existing
`apt-get upgrade -y`; changing that policy is a recommendation awaiting Bob.

Bob can run this exact read-only comparison on each device from its checkout
(no package install, restart or network request):

```sh
cd ~/bopOS
~/venv/bin/python - <<'PY'
import importlib.metadata as metadata
import platform
from pathlib import Path
import re
import sys

def key(name):
    return re.sub(r"[-_.]+", "-", name).lower()

installed = {key(d.metadata["Name"]): d.version for d in metadata.distributions()}
expected = {}
for line in Path("constraints.txt").read_text().splitlines():
    if not line or line.startswith("#"):
        continue
    pin, _, marker = line.partition(";")
    if marker and ((sys.version_info[:2] >= (3, 10)) != (">=" in marker)):
        continue
    name, version = pin.split("==")
    expected[key(name)] = version
print("Python", platform.python_version(), platform.machine())
for name, version in sorted(installed.items()):
    wanted = expected.get(name)
    if wanted:
        print(name, version, "OK" if version == wanted else "DIFF expected " + wanted)
for line in Path("python/requirements.txt").read_text().splitlines():
    if line and not line.startswith(("#", "-")) and key(line) not in installed:
        print(key(line), "MISSING expected", expected.get(key(line), "unconstrained"))
PY
cat /etc/os-release
dpkg-query -W -f='${Package} ${Version}\n' puredata puredata-core jackd2 libjack-jackd2-0
```

### Updating deliberately

Change pins as a reviewed maintenance task, never as an implicit show-time
upgrade. Capture the working environment, resolve candidate versions in a new
scratch venv, and update the exact constraints (including transitives and the
Python 3.9 branch). Leave the working show venv intact until verification and
review are complete. Inspect `Requires-Python` and platform-specific dependencies;
a macOS install cannot certify a Pi's binary builds or mixer/sensor behavior.

For example, validate the resulting files from the repository root with a
fresh directory outside the checkout (use a new path on each update):

```sh
python3 -m venv /tmp/bopos-pins-check
/tmp/bopos-pins-check/bin/python -m pip install -r requirements-dev.txt
/tmp/bopos-pins-check/bin/python -m pip check
/tmp/bopos-pins-check/bin/python -m playwright install chromium --only-shell
BOPOS_PYTHON=/tmp/bopos-pins-check/bin/python ./tools/run-tests.sh fast
BOPOS_PYTHON=/tmp/bopos-pins-check/bin/python ./tools/run-tests.sh browser
```

Repeat with Python 3.9 when retaining that floor. Node/library pin changes also
need Bob's rig comparison and relevant peripheral/audio checks before claiming
hardware compatibility. Record versions, commands and results with the stitch.
The constraints fix package versions, not artifact hashes, the interpreter,
Node.js, or OS package versions; build tools remain platform prerequisites.
