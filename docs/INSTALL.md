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

## 2. Prepare the system

Boot the Pi and log in (`ssh pi@raspberrypi.local`), then:

```sh
sudo raspi-config nonint do_expand_rootfs
sudo raspi-config nonint do_i2c 0
sudo apt-get update
sudo apt-get upgrade -y
echo "jackd2 jackd/tweak_rt_limits boolean true" | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  jackd2 puredata git python3-pip python3-venv i2c-tools
```

## 3. Install bopOS

```sh
python3 -m venv ~/venv
git clone --recursive https://github.com/zealtv/bopOS.git ~/bopOS
~/venv/bin/pip install -r ~/bopOS/python/requirements.txt
cd ~/bopOS
sudo bash/provision.sh
```

`provision.sh` is the **one-time privileged step**. It installs the boot
entry, the validated hostname helper, and narrow sudoers rules that let the
unprivileged node software reboot, power off, or apply a hostname — and
nothing else. Everything after this runs as `pi`.

> Existing fleet Pis that predate the hostname helper need one manual
> `sudo bash/provision.sh` after updating; the routine **Update bopOS**
> action deliberately cannot install root-owned pieces.

## 4. Point it at the audio board

JACK opens the ALSA card named by `SOUNDCARD` (default `DigiAMP` in
`bash/start-engine.sh`). Check what your board is called and set it if it
differs:

```sh
cat /proc/asound/cards
```

A board bopOS hasn't been benched on must be checked for playback **and**
engine-safe mute before you trust it in a show — follow the bench procedure
in [HARDWARE.md](HARDWARE.md) and add your row to its table.

If you're using I2C peripherals, confirm the bus sees them:

```sh
i2cdetect -y 1
```

## 5. First contact

Reboot the node. On the dashboard machine (see
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
