# bopOS

bopOS is a Raspberry Pi framework for networked, multi-device sound and
interactivity. A fleet of small computers runs autonomous sound patches while a
web dashboard handles discovery, assignment, control, spatial authoring, patch
management, and synchronized cues over Wi-Fi.

- Pure Data is the reference sound engine; SuperCollider is also supported
  through the same engine boundary.
- Python owns fleet administration, OSC routing, persistence, clock sync, asset
  delivery, and direct I2C peripherals.
- Each node can keep playing without the dashboard or network once it has been
  configured.
- The [bop](https://github.com/zealtv/bop) Pure Data module library is included
  as a submodule.

> **Status — July 2026:** the OSC v1.2 engine boundary, web dashboard, patch
> manifest, master/point/cue terms, and macOS audition rig are implemented. The
> equivalent Linux/JACK audition run and several installation-scale hardware
> gates remain open. The current architecture and work state live in
> [CLAUDE.md](CLAUDE.md), [the OSC contract](docs/OSC-CONTRACT.md), and
> [`.loom/`](.loom/).

## System at a glance

```text
web dashboard                         each bopOS node
  sends fleet commands on UDP 6660      bopos.py: sole LAN listener
  receives heartbeats on UDP 5550          ├─ engine surface on localhost 6661
  authors room, points and cues             ├─ engine requests on localhost 7770
                                              └─ I2C bridge on 6662 / 8880
```

`bopos.py` is the node's only LAN-facing process. It matches the device
selector, performs framework work, and relays a selector-free surface to the
active sound engine. Patches do not bind fleet ports or perform administrative
operations.

## Requirements

For a production node:

- Raspberry Pi running Raspberry Pi OS Lite 64-bit (Pi Zero 2 W is supported)
- an audio output supported by ALSA/JACK, such as an IQaudio DigiAMP+
- a Wi-Fi network shared with the dashboard machine during setup and control
- optional I2C sensors, buttons, ADCs, touch controllers, or displays

The current image/bootstrap scripts use the `pi` account and
`/home/pi/bopOS`. The wire protocol itself does not depend on that username or
on any particular Pi, audio board, Wi-Fi interface, or sound engine.

## Install a Raspberry Pi node

Flash **Raspberry Pi OS Lite (64-bit)** with Raspberry Pi Imager. In the Imager
settings:

1. create the `pi` user and a password;
2. configure the installation Wi-Fi;
3. enable SSH.

Log in and prepare the system:

```sh
ssh pi@raspberrypi.local

sudo raspi-config nonint do_expand_rootfs
sudo raspi-config nonint do_i2c 0
sudo apt-get update
sudo apt-get upgrade -y
echo "jackd2 jackd/tweak_rt_limits boolean true" | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  jackd2 puredata git python3-pip python3-venv i2c-tools

python3 -m venv ~/venv
git clone --recursive https://github.com/zealtv/bopOS.git ~/bopOS
~/venv/bin/pip install -r ~/bopOS/python/requirements.txt
cd ~/bopOS
sudo bash/provision.sh
```

`provision.sh` is the one-time privileged step: it installs the current
`rc.local` boot entry, the validated hostname helper, and narrow sudoers rules
that permit the unprivileged bopOS helper to reboot, power off, or apply a
validated hostname. Routine dashboard updates are
orchestrated by the already-running helper as `pi`, so checking out a branch
cannot replace the update procedure mid-operation. The helper restores and
pulls the checkout without interactive Git credentials, preserves
`patches/active_patch.txt`, updates submodules, issues the convergence receipt,
and only then requests a reboot. `update.sh` remains the equivalent manual
convergence check and never reboots. Do not keep uncommitted work on an
installation node.

Before relying on audio, set the ALSA card name used by JACK. The current
default is `DigiAMP` in `bash/start-engine.sh`:

```sh
cat /proc/asound/cards
```

New audio boards must be benched for playback and engine-safe mute; follow
[docs/HARDWARE.md](docs/HARDWARE.md). To confirm the I2C bus is visible:

```sh
i2cdetect -y 1
```

## Run the dashboard

The dashboard at `/` is organised into Dashboard, Seats, Devices, Patches,
Assets, and Sequencer tabs. `/facilitator` remains a standalone compatibility
entry for the touch-first Dashboard surface.

One-time laptop setup:

```sh
python3 -m venv ~/.venvs/bopos
~/.venvs/bopos/bin/pip install -r dashboard/requirements.txt pyOSC3
```

Run it on the installation LAN:

```sh
~/.venvs/bopos/bin/python dashboard/server.py --host 0.0.0.0
```

Open <http://localhost:8080/>. Nodes appear from their heartbeats; no static
device list is required. The tabbed application provides:

- discovery, identify, naming, ID assignment, and element positioning;
- manifest-declared patch parameters and master control;
- patch add/switch/pull and framework lifecycle actions;
- room, point, listener, venue, and preset authoring;
- synchronized named cues and engine/device health.

The Dashboard tab exposes master, safety controls, presets, and only the patch
parameters explicitly promoted with `"facilitator": true`. Venue-promoted
framework commands appear at explicit fleet and single-device scopes.

See [dashboard/README.md](dashboard/README.md) for configuration, simulator
options, venue state, and clock measurement.

## Device identity and assignment

Every node has a stable `uid` (normally its primary-interface MAC address) and
a numeric installation ID. A new node that has never been configured starts as
ID `-1`, continues running, and announces itself quickly until assigned.

Use the dashboard to identify the physical box, give it a name and ID, and drag
its element outputs onto the room map. The full assignment is persisted on the
node and in the dashboard, then replayed whenever the device reappears.

`bopos.devices` remains an optional CSV seed for existing fleets and hostnames;
it is not the source of truth and an unknown MAC never prevents a node from
starting. Boot resolution is:

```text
persisted assignment → bopos.devices seed → unassigned (ID -1)
```

## Patches and sound engines

A patch is a folder under `patches/<name>/`; it may be host-mirrored or an
independent Git repository. The selected name is stored in
`patches/active_patch.txt`. Every patch declares its engine, entry point,
parameters, capabilities, and asset slots in `bopos.patch.json`:

```json
{
  "engine": "pd",
  "entrypoint": "main.pd",
  "params": [
    {
      "path": ["synthesis", "voice"],
      "name": "density",
      "type": "f",
      "min": 0,
      "max": 1,
      "default": 0.5,
      "facilitator": true
    }
  ],
  "caps": [],
  "slots": ["samplepacks"]
}
```

The manifest is authoritative: PD is the reference engine, not a hard-coded
requirement. A missing or invalid manifest fails launch loudly; there is no
implicit `main.pd` fallback.

Use the dashboard to add a GitHub patch, switch the active patch, pull its
latest revision, or fetch assets. These actions target one device or the whole
fleet and use the `/os/*` administration plane described in the
[OSC contract](docs/OSC-CONTRACT.md).

### Patch-side boundary

The engine receives this selector-stripped localhost surface:

```text
/id <n>
/os/master <0..1>
/p/<segment>[/<segment>...] <values...>
/pt <point> <element> <value>
/cue <cue-id>
/notify <event>
```

The framework provides values; the patch decides what they mean. Master belongs
at the final output stage, point values can drive any patch behavior, and a cue
is already scheduled before the engine sees it. Ignoring an unused term is
legal.

Parameter `name` is the leaf OSC segment. An optional manifest `path` array
supplies its parents, so `{"path":["synthesis","voice"],"name":"density"}`
has canonical identity `synthesis/voice/density` and reaches every engine as
`/p/synthesis/voice/density`. Existing declarations without `path` remain flat
and unchanged.

Pure Data patches receive the surface through `[bopos]` (`pd/bopos.pd`) and
normally finish through `[bopos.out~]`, which applies master and the private
audition preview safely at the output boundary. The tracked
[`demo-pd`](patches/demo-pd/) and [`demo-sc`](patches/demo-sc/) patches are
copyable starting points for the two engines.

Framework-owned run context is delivered atomically at launch: reproducible
seed, opaque run ID, patch name, asset root, and engine port. Engines never need
absolute wall-clock time for synchronized cues.

## OSC ports

UDP ports are fixed in production. Only 5550 and 6660 cross the network; the
rest are localhost plumbing on each node.

| Port | Listener | Sender | Purpose |
|---:|---|---|---|
| 5550 | dashboard | `bopos.py` | heartbeat, status, and command replies |
| 6660 | `bopos.py` | dashboard | selected fleet commands |
| 6661 | active engine | `bopos.py` | selector-stripped engine surface |
| 6662 | active engine | `io/main.py` | bundled peripheral data |
| 7770 | `bopos.py` | active engine | engine requests: config, store, load, report |
| 8880 | `io/main.py` | active engine | peripheral and I/O commands |

The normative addresses, ownership rules, persistence model, patch manifest,
sync encoding, and provided terms are in
[docs/OSC-CONTRACT.md](docs/OSC-CONTRACT.md).

## Direct I2C peripherals

`python/io/main.py` polls configured peripherals (10 Hz by default), sends one
OSC bundle to the engine, and accepts localhost commands on 8880:

```text
/io/create tilt lis3dh 0x19
/io/poll 20
/io/report
/io/scan 1
```

Built-in modules cover LIS3DH, ADS1015, ADS1115, MPR121, switches, and SSD1306
displays. Copy `python/io/io_template.py` to add another device. Details and
the peripheral command shape are in
[python/io/README.md](python/io/README.md).

## Develop without a fleet

### Protocol-only simulated nodes

Run the dashboard in one terminal and a five-device simulated fleet in another:

```sh
~/.venvs/bopos/bin/python dashboard/server.py
~/.venvs/bopos/bin/python tools/simfleet.py --devices 5
```

The simulator speaks the real heartbeat and command protocol but produces no
audio.

### Audible laptop fleet

`tools/audition.py` launches multiple real instances of the selected patch
behind one fleet command socket:

```sh
~/.venvs/bopos/bin/python dashboard/server.py --osc-target 127.0.0.1
~/.venvs/bopos/bin/python tools/audition.py --devices 3 \
  --bind 127.0.0.1 --target 127.0.0.1 \
  --manifest patches/demo-pd/bopos.patch.json
```

On macOS it defaults to CoreAudio; on Linux it defaults to JACK. Drag the white
listener puck and edit its heading to hear the room from that perspective.
Normal production output remains identity/bypass when no audition positions are
present.

### One local patch and I2C bridge

`bash/start-laptop.sh` and `bash/stop-laptop.sh` run the active PD patch with
the I2C bridge on a laptop using an MCP2221A USB adapter. Configure `PD_BIN` and
`PYTHON_BIN` at the top of `start-laptop.sh` first.

Verification is proportional to the change; the project test matrix and venv
conventions are in [docs/VERIFICATION.md](docs/VERIFICATION.md).

## Repository layout

```text
bash/        boot, engine lifecycle, update, patch and asset scripts
dashboard/   FastAPI/WebSocket server and browser interfaces
docs/        OSC contract, hardware, performance, and verification guides
patches/     active patch selection and installed patch repositories
pd/          bopOS Pure Data adapters and the bop submodule
python/      node service, persistence, sync, spatial math, and I2C bridge
tools/       simfleet, audible audition rig, sync and performance harnesses
.loom/       live work tracker and retained stitch evidence
.notes/      current design and handoff notes
.lore/       dated design decisions and council records
```

## Further reading

- [Dashboard guide](dashboard/README.md)
- [OSC contract v1.5](docs/OSC-CONTRACT.md)
- [Audio hardware onboarding](docs/HARDWARE.md)
- [Verification matrix](docs/VERIFICATION.md)
- [Performance measurement](docs/PERF.md)
