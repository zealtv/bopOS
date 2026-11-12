# Changelog

One entry per release, newest first. Each entry names the compatibility facts
for that release: the OSC contract version, the provision level and the
project storage schema. Releases with the same major number interoperate in
one fleet. See [docs/releasing.md](docs/releasing.md) for the cycle.

## v1.0.0 (2026-11-12): contract 1.26 · provision level 1 · schema 1

The first numbered release. It collects the framework as it stood in November
2026. Earlier development had no version numbers.

- **Nodes.** Each Raspberry Pi runs its patch locally under systemd. A patch
  is a folder with a manifest declaring its controls. The node keeps playing
  with no network and no laptop present. It sends heartbeats, fires
  clock-synced events, and reports its patch, framework revision and update
  model.
- **Engines.** Pure Data is the supported engine. A SuperCollider demo patch
  ships, but it has not yet been updated to the current contract or run under
  this release.
- **Dashboard.** A FastAPI/WebSocket server with a browser UI. It discovers
  nodes, places them on the room map, distributes patches and assets, and gives
  a performer live control, including a master fader and mute for the room.
  Projects hold the installation's setup. The Devices roster and the header
  show each release (`1.0.0`, or `1.0.0+dev.12` between releases), with the
  git hash on hover. A read-only **Settings** tab shows the dashboard host's
  release, build, git hash, OSC contract and storage schema.
- **Wire.** The OSC contract at version 1.26 ([docs/OSC-CONTRACT.md](docs/OSC-CONTRACT.md)).
  `/os/report` gains an optional `release` string, the node's display version
  (`1.0.0`, or `1.0.0+dev.12.gabc1234` between releases). Heartbeats and the
  update receipt still carry the git hash.
- **Inputs.** I2C peripherals through the node's IO bridge. USB keyboard and
  mouse devices, such as a Makey Makey, reach the patch as `/io/key` and
  `/io/mouse`, verified on hardware. Simulated input and input forwarded from a
  node work in Patch Edit. OSC input from outside apps is routed through the
  dashboard.
- **Updates.** **Update bopOS**, per device or for the fleet, runs unattended,
  reports its phases and reboots only after success. When an update needs new
  privileged setup (a higher provision level), it refuses before changing
  anything. `bopos update` on the device runs that setup with `sudo`. Patches
  reach devices only by dashboard distribution.
- **Releases.** From this version on, devices track public `main`, which
  receives one tagged commit per release ([docs/releasing.md](docs/releasing.md)).
  The tree carries a `VERSION` file, and `bopos version` prints it.
- **A fresh public history.** v1.0.0 is the first commit of this repository.
  A device installed from an earlier checkout can't fast-forward to it; move it
  once over SSH, as [docs/INSTALL.md](docs/INSTALL.md) describes ("Moving a
  device from before v1.0.0"). Update bopOS refuses cleanly until then.
