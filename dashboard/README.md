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

# real fleet (Pis running helper.py already on the LAN; align an external
# GPIO/click recording to the printed fire schedule -- this is the sync-4 run):
~/.venvs/bopos/bin/python tools/sync_measure.py --mode hardware --cues 8
```

Sim spread is a single-machine floor; the honest number is the hardware run.

## Spatial automation (Stage A)

A moving point places sound across the fleet: each device's gain is
`falloff(distance from the point, radius)`, computed by the dashboard from the
device positions and folded into the volume param it already sends — composed as
**stored mix × master × spatial**, runtime-only (never persisted). This is the
dashboard-computed per-device `/p/gain` first implementation (contract §4, fine
≤ ~12 nodes / on the audition rig); node-side `/pt` falloff for larger fleets is
Stage B.

Drive it over `/ws` with a full-state `set_spatial` message (the surface
spatial-1's map UI will author):

```jsonc
{"type": "set_spatial", "data": {
  "active": true, "radius": 4.0, "falloff": "smooth",   // linear | smooth | gauss
  "motion": {"type": "static", "point": [5, 4]}          // or path / orbit
}}
```

`motion` is `static` (a fixed/drag point), `path` (`points`, `duration`, `loop`
— a polyline sweep), or `orbit` (`center`, `radius`, `period` — a circular LFO).
A still point applies once; a moving one re-sends at ~25 Hz. `active: false`
restores plain stored × master. The math lives in `spatial.py`; the engine and
its tick loop in `osc_bridge.py`.

## Flags

`--port` HTTP port (8080) · `--listen-port` OSC in (5550) · `--send-port` OSC
out (6660) · `--osc-target` unicast/broadcast target (255.255.255.255) ·
`--state-file` installation.json path · `--assets-dir` served at `/assets`
for `/os/fetch`.

State lives in `dashboard/installation.json` (devices, positions, room,
master, presets); named snapshots in `dashboard/installations/<venue>.json`
via the Venue save/load buttons. Both are gitignored.
