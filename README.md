# bopOS

A Raspberry Pi + Pure Data framework for **networked multi-device sound and interactivity**.

- Pis run autonomous **bop** / Pure Data audio patches, administered and controlled over WiFi (OSC).
- **Python** provides admin services (update, reboot, shutdown, patch management) and **I2C input/
  output** (sensors, buttons, displays) — no microcontroller or soldering required.
- Plays well with the [bop](https://github.com/zealtv/bop) module library for PD Vanilla.

> **Status (2026-06):** bopOS was brought up to date with its fork
> [plantsOS](https://github.com/playablestreets/plantsOS) and is now the canonical line —
> plantsOS systems migrate back to bopOS over time. The architecture is **I2C-direct** (the old
> ESP32 + serial path is archived under `legacy/arduino/`). See `.notes/architecture-overview.md`.

# Requirements

- Raspberry Pi (any model; **Pi Zero 2 W** supported)
- A Raspberry Pi soundcard (e.g. DigiAmp+ / IQaudio / HiFiBerry, i2s)

# Installation and Setup

## Flash SD using Raspberry Pi Imager

- Choose OS **RASPBERRY PI OS LITE (64-BIT)**
- Set username **`pi`** and a password
- Configure wireless LAN
- Enable SSH
- Flash SD

## Install packages

### login

```
ssh pi@raspberrypi.local
```

### run this one-liner

```
sudo raspi-config nonint do_expand_rootfs; sudo raspi-config nonint do_i2c 0; sudo apt-get update; sudo apt-get upgrade -y; echo "jackd2 jackd/tweak_rt_limits boolean true" | sudo debconf-set-selections; sudo DEBIAN_FRONTEND=noninteractive apt-get install -y jackd2; sudo apt-get install puredata git pip i2c-tools -y; cd ~; python3 -m venv ./venv; git clone --recursive https://github.com/zealtv/bopOS.git; ~/venv/bin/pip install -r ~/bopOS/python/requirements.txt; sleep 5; sudo ~/bopOS/bash/update.sh;
```

This expands the filesystem, enables I2C, installs jackd2 + Pure Data + git + i2c-tools, creates a
Python venv, clones bopOS (with the `bop` submodule), installs the Python deps, and runs
`update.sh` — which copies `rc.local` and reboots with jack, Pure Data, `io/main.py`, and
`helper.py` running.

- You may need to edit **`bash/start.sh`** to set your `SOUNDCARD` (default `DigiAMP`). List cards
  with `cat /proc/asound/cards`.
- Run `i2cdetect -y 1` to check for connected I2C devices.

## Device identity

`bopos.devices` maps **MAC → hostname, ID, position**. On boot, `helper.py` reads the Pi's MAC,
sets its hostname, and reports its ID to Pure Data. Add each Pi here.

```
MAC, hostname, ID,  POSL, POSR
b8:27:eb:b4:64:79, bobop, 111, 0 0, 0 0
```

# Patches (the sound engine)

A **patch** is a hot-swappable git repo under `patches/`, entry point `main.pd`. The active patch
is named in `patches/active_patch.txt`. From `DASHBOARD.pd` (or any OSC sender) on the same
network:

```
/addpatch <gituser> <reponame>   # clone a patch repo onto the Pi (recursive)
/patch <reponame>                # switch active patch + reboot
/pullpatch                       # git pull the active patch
/getsamples                      # fetch sample packs (gdrive) per the patch's bopos.config
```

A patch may include an optional `bopos.config` (shell vars like `SAMPLEPACKSURL`) and a
patch-specific `start.sh`. See `patches/README.md`.

> **PD-agnostic by design:** bopOS talks to its sound engine purely over OSC, and a patch declares
> its own entry. Pure Data is the preferred/reference engine, but the OSC contract below is not
> PD-specific — another engine could sit on the same ports.

# OSC architecture

UDP. The laptop (`DASHBOARD.pd`) only needs ports **5550** (listen) and **6660** (send); the rest
are localhost-only on each Pi.

| Port | Direction | Purpose |
|------|-----------|---------|
| 5550 | Pi → Laptop (broadcast) | device status / heartbeat |
| 6660 | Laptop → Pi (broadcast) | commands to devices |
| 6661 | helper.py → PD (localhost) | helper/admin responses |
| 6662 | io/main.py → PD (localhost) | sensor data bundles |
| 7770 | PD → helper.py (localhost) | admin commands |
| 8880 | PD → io/main.py (localhost) | I/O commands |

## MAIN / patch (`patches/<active>/main.pd`)

Runs on Pis. Generates audio; routes OSC via `pd/bopos.osc.pd`. Forwards `/helper/*` to
`helper.py` (7770) and `/io/*` to `io/main.py` (8880); reports to the laptop on 5550.

## helper.py (port 7770)

Runs on Pis. OS/admin over OSC: `/update` `/reboot` `/shutdown` `/getsamples` `/checkout`
`/config`, and patch management `/patch` `/addpatch <user> <repo>` `/pullpatch`.

## io/main.py (port 8880)

Runs on Pis. **I2C → OSC bridge.** Polls all configured peripherals at a rate (default 10 Hz) and
sends a single OSC bundle to PD on 6662. Create peripherals dynamically:

```
/io/create <name> <type> <0xADDR>   e.g.  /io/create tilt lis3dh 0x19
/poll <hz>                          set the poll rate
/report                             list active peripherals
```

Built-in peripheral types live in `python/io/` (`io_lis3dh.py`, `io_ads1015.py`, `io_ads1115.py`,
`io_mpr121.py`); copy `io_template.py` to add more. See `python/io/README.md`.

## ADMIN (`DASHBOARD.pd`)

Runs on a laptop. Monitors and controls the Pis: broadcasts commands to 6660, listens for status
on 5550.

# Repo layout

```
bopOS/
├── bash/          boot, start/stop, update, sample + patch management
├── python/
│   ├── helper.py  admin/OS OSC service
│   └── io/        I2C-to-OSC bridge + per-peripheral modules
├── pd/            bopos.osc / feedback / gui patches + bop submodule
├── patches/       hot-swappable git-repo patches (active_patch.txt)
├── bopos.devices  MAC → hostname/ID/position
├── DASHBOARD.pd   laptop admin/control patch
├── legacy/arduino archived ESP32 sketches (out of the boot path)
└── .notes/        architecture + design notes
```

# Laptop dev workflow

`bash/start-laptop.sh` / `stop-laptop.sh` run bopOS on a laptop (Pure Data + `io/main.py`) using an
MCP2221A USB-to-I2C adapter — useful for developing patches and peripherals without a Pi.
