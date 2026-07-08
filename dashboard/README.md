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
  params, patch management, discovery/assignment, venues, presets.
- **<http://localhost:8080/facilitator>** — facilitator view: volume cards,
  master, Silence All, Sound check, preset picker. On an iPad, "Add to Home
  Screen" launches it fullscreen.

Useful simfleet variations: `--unassigned 2` (exercise discovery/assign),
`--engine-dead 1` (a crashed engine), `--drop 0.05 --jitter-ms 30` (bad WiFi),
`--manifest path/to/bopos.patch.json` (serve a different param declaration).

## Real fleet

On the installation LAN the defaults already match the OSC contract (listen
5550, send 6660, broadcast target). Run the server on any machine on that
network; real nodes appear as they heartbeat:

```sh
~/.venvs/bopos/bin/python dashboard/server.py --host 0.0.0.0
```

## Flags

`--port` HTTP port (8080) · `--listen-port` OSC in (5550) · `--send-port` OSC
out (6660) · `--osc-target` unicast/broadcast target (255.255.255.255) ·
`--state-file` installation.json path · `--assets-dir` served at `/assets`
for `/os/fetch`.

State lives in `dashboard/installation.json` (devices, positions, room,
master, presets); named snapshots in `dashboard/installations/<venue>.json`
via the Venue save/load buttons. Both are gitignored.
