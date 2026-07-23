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
absent, and enables `bopos.service`. It is safe to rerun: existing device config
is preserved, and an existing checkout is only fast-forwarded.

The default system locale is `en_AU.UTF-8`. To choose another UTF-8 locale:

```sh
curl -fsSL https://raw.githubusercontent.com/zealtv/bopOS/main/install-device.sh |
  env LANG=C LC_ALL=C BOPOS_LOCALE=en_GB.UTF-8 bash
```

The installer generates the locale, sets `LANG`, and removes stale global
`LC_ALL`/`LANGUAGE` overrides that otherwise produce warnings or confuse Python
package installation.

Review the reference DigiAMP+ defaults before rebooting:

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
  alsa-utils jackd2 puredata git python3-pip python3-venv i2c-tools locales
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
service, the validated hostname helper, the initial device config, and narrow
sudoers rules that let the unprivileged node software reboot, power off, or
apply a hostname — and nothing else. Everything after this runs as `pi`.

> Existing fleet Pis that predate the hostname helper need one manual
> `sudo bash/provision.sh` after updating; the routine **Update bopOS**
> action deliberately cannot install root-owned pieces.

## 4. Point it at the audio board

JACK opens the ALSA card named by `SOUNDCARD`; installation defaults to the
verified DigiAMP+ pairing in `bopos.config`:

```sh
SOUNDCARD=DigiAMP
MIXER_CONTROL=Digital
```

Check what your board is called and edit those values if it differs:

```sh
cat /proc/asound/cards
nano ~/bopOS/bopos.config
```

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
