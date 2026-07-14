# bopOS dashboard

Web control surface for the fleet: tech view at `/`, facilitator view at
`/facilitator`.

## Quickstart (laptop, no hardware)

One-time setup:

```sh
python3 -m venv ~/.venvs/bopos
~/.venvs/bopos/bin/pip install -r dashboard/requirements.txt python-osc
```

Run the server (terminal 1, from the repo root):

```sh
~/.venvs/bopos/bin/python dashboard/server.py
```

Run a simulated fleet to play against (terminal 2):

```sh
~/.venvs/bopos/bin/python tools/simfleet.py --devices 5
```

Then open:

- **<http://localhost:8080/>** — tech dashboard: device list, spatial map,
  listener audition puck, point authoring
  (drag/radius/falloff/two-axis wall bounce), params, patch
  management, host-to-node patch and asset distribution, discovery/assignment,
  synced named cues, venues, presets.
- **<http://localhost:8080/facilitator>** — facilitator view: device cards
  with the patch's promoted (`facilitator: true`) params as labelled controls,
  master, Silence All, preset picker. On an iPad, "Add to Home
  Screen" launches it fullscreen.

Useful simfleet variations: `--unassigned 2` (exercise discovery/assign),
`--engine-dead 1` (a crashed engine), `--drop 0.05 --jitter-ms 30` (bad WiFi),
`--manifest path/to/bopos.patch.json` (serve a different param declaration).

When `tools/audition.py` runs on the dashboard machine, drag the white listener
puck to preview the installation from that position; edit its heading above the
map. The dashboard sends the complete listener state only to loopback port 6660,
where the audition relay derives and forwards fixed-stereo matrices. This
private preview state is never broadcast onto the installation LAN and is not
part of the fleet OSC contract.

The dashboard's **Start simulation** control manages this audition rig directly:
every valid folder under `patches/` is already available, and one selected patch
runs across the whole simulated fleet. Use the Patch dropdown and **Switch** to
restart the managed engines into another host patch. Send/Sync is intentionally
absent in this mode because there is no remote filesystem to converge.

`tools/simfleet.py` is different: it is the protocol-only remote-node harness.
It retains `/os/fetch` queue and receipt behaviour so distribution itself can be
tested without hardware.

## Real fleet

On the installation LAN the defaults already match the OSC contract (listen
5550, send 6660, broadcast target). Run the server on any machine on that
network; real nodes appear as they heartbeat:

```sh
~/.venvs/bopos/bin/python dashboard/server.py --host 0.0.0.0
```

## Clock sync & cue timing

The dashboard is the clock leader: while it runs it broadcasts `/sync/ping`,
estimates each node's clock offset, and pushes `/<id>/sync/offset` so a broadcast
`/cue <cueId> <sharedTimeNs>` fires sample-tight(ish) across the fleet (contract
§3.1). Nothing to enable — it's on whenever the server is up.

To measure how tight cues actually land, `tools/sync_measure.py` fires a cue
burst and reports the cross-device spread:

```sh
# software floor (launches simfleet itself, writes a Markdown report):
~/.venvs/bopos/bin/python tools/sync_measure.py --devices 5 --sync-skew-ms 40

# real fleet (Pis running bopos.py already on the LAN; align an external
# GPIO/click recording to the printed fire schedule -- this is the sync-4 run):
~/.venvs/bopos/bin/python tools/sync_measure.py --mode hardware --cues 8
```

Sim spread is a single-machine floor; the honest number is the hardware run.

## Flags

`--port` HTTP port (8080) · `--listen-port` OSC in (5550) · `--send-port` OSC
out (6660) · `--osc-target` unicast/broadcast target (255.255.255.255) ·
`--state-file` installation.json path · `--assets-dir` host asset folders served
at `/assets` · `--patches-dir` host patch folders served at `/patches` ·
`--public-url` URL nodes should fetch from. When the dashboard is opened through
`localhost`, it derives the LAN source address from each real device's route;
the explicit flag remains useful on multi-interface or proxied installations.

The defaults are the repository's `assets/` and `patches/` directories. Select
a device, then Send one folder or Sync all folders. A successful receipt marks
that host manifest in sync; after editing a host folder, Refresh host folders
marks the prior receipt stale.
The installed Patch dropdown is node-reported inventory, not the host catalog:
a new host patch appears there only after its Send completes successfully.
Sending a device's active patch is confirmation-gated because its engine stops
and restarts. A ◆ marker identifies Git-managed device patches: update those
with Pull latest; host-mirrored patches use Send.
Selecting an installed patch with **Switch** also restarts only the engine stack;
the helper, dashboard connection, and operating system stay online. After the
replacement starts, the dashboard refreshes the active report and parameter
declarations from the node.

State lives in `dashboard/installation.json` (devices, positions, room,
visual coordinate origin, listener, master, presets). The technical view lets
you type each element's x/y relative to that origin; the dashboard converts it
through the same assignment path used by map dragging. Named snapshots live in
`dashboard/installations/<venue>.json`
via the Venue save/load buttons. Both are gitignored.

The facilitator is fail-closed. Patch parameters appear there only when their
manifest declaration has `"facilitator": true`. Framework commands default to
none; a venue may opt in supported fleet-wide commands in its installation
state, for example:

```json
{"facilitator_commands": ["restart-engine"]}
```

Command controls are confirmation-gated, and destructive commands require a
hold. The allowlist belongs to the installation, never the patch manifest.
