# Verification

Date: 2026-07-26

## Focused static and living checks

```sh
git diff --check
node --check dashboard/static/js/monitor.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile dashboard/osc_bridge.py dashboard/server.py \
  tests/test_osc_transport.py tests/verify_osc_transport_monitor.py \
  .loom/threads/44-fresh-device-access/\
2-macos-osc-routing-shutdown.stitching/verify_imani_adoption.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m unittest -v tests.test_osc_transport tests.test_device_control_routing
```

Passed. The focused transport suite has eight checks covering:

- errno 49 containment across a complete first heartbeat;
- throttling by destination/errno and success-only `osc_out`;
- destination-selected LAN versus loopback sockets;
- cached peer discovery and rebind-for-later-send behavior;
- direct-LAN `SO_DONTROUTE` selection plus routed-venue fallback;
- exception-safe shutdown and already-off no-send behavior;
- the bounded accessible System transport-error log contract.

The adjacent living device-routing suite passed five checks.

## Browser and adjacent route/mode checks

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_osc_transport_monitor.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/2-dual-route-transport/verify_dual_route.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_device_control_modes.py
```

Passed 5/5 Monitor checks, 7/7 dual-route checks, and 16/16 device-control mode
checks. The real dashboard/System panel rendered destination, errno, failed OSC
address, and actionable socket text with no browser error. Physical
administration remained on the installation destination through Live,
Simulation, and Patch Edit, while execution traffic retained its loopback mode
switch.

The archived
`.loom/tied/01-simulation-transition-coherence/verify_simulation_transition.py`
was also run. Its first backend check passed, then its stale Live-restore
assertion failed because it expects assignment replay. Current ratified living
coverage deliberately requires restore to send only master and MUTE ALL and no
physical assignment/device state. Its browser half subsequently timed out on
retired DOM. This is known tied-guard rot, not a product regression; no product
behavior was changed to satisfy it.

## Imani Silver hardware adoption

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/44-fresh-device-access/\
2-macos-osc-routing-shutdown.stitching/verify_imani_adoption.py
```

The verifier launched the real dashboard with a temporary copy of
`dashboard/installation.json`, the production report/command ports
`5550`/`6660`, and deliberately no `--osc-target`.

Observed hardware:

- Mac interface: `en0`;
- Mac interface/source address: `192.168.0.100`;
- heartbeat peer: Imani Silver, `192.168.0.103`,
  `b8:27:eb:b4:64:79`;
- destination: `255.255.255.255:6660`;
- device checkout: `dbb1bf3`;
- existing safe binding replay: Seat 2.

Passed 10/10 checks:

- online discovery through the default target;
- report, patch inventory, and asset inventory;
- Device enabled acknowledgement and effective output-enabled state;
- assignment convergence on the existing Seat 2 binding;
- explicit `request_patches` administration command and `/os/patches` receipt;
- no browser page errors;
- logged source binding:
  `OSC LAN sender bound to 192.168.0.100 for peer 192.168.0.103`;
- Uvicorn `Application shutdown complete` with no shutdown failure.

The first hardware attempt exposed a competing `utun4` route for
`192.168.0/24`: ordinary UDP-connect selected tunnel address
`100.113.184.66`, so commands still failed. A direct `SO_DONTROUTE` probe
selected `192.168.0.100`; after that correction the full gate passed.

One pre-heartbeat `/sync/ping` still encounters errno 49 because no physical
peer is known yet. It is now contained and logged, the heartbeat selects the
LAN source, and all subsequent traffic succeeds. This bounded initial
operational signal is the intended behavior. No reboot, shutdown, update,
patch switch, asset transfer/removal, or audible cue was exercised.
