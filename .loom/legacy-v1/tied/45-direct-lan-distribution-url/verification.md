# Verification

Date: 2026-07-26

## Cause

`54ff063` made OSC source selection direct-LAN-first because ordinary macOS
route lookup for Imani Silver (`192.168.0.103`) selected the overlapping
Tailscale route and source (`100.113.184.66`). `Dashboard.public_url()` retained
its own ordinary UDP-connect probe, so a patch deployment initiated from
`http://localhost:8080/` advertised the unreachable Tailscale source to the
LAN-only Pi.

The failed node receipt was:

```text
FETCH http://100.113.184.66:8080/patches/bonks-pd/.manifest.json
patch:bonks-pd: err (<urlopen error timed out>)
```

The LAN endpoint returned HTTP 200 from the Pi. Retrying through a WebSocket
connected to `192.168.0.100:8080` fetched and switched Imani successfully.

## Change

The direct-LAN-first `SO_DONTROUTE` probe is now the shared
`osc_bridge.source_for_peer()` helper. OSC retains its routed-venue fallback,
and localhost-originated IPv4 patch/asset URL derivation uses the same helper.
Explicit `--public-url`, non-loopback browser hosts, loopback nodes, and IPv6
retain their prior paths.

## Checks

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile dashboard/osc_bridge.py dashboard/server.py \
  tests/test_osc_transport.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m unittest -v tests.test_osc_transport
```

Passed 9/9. The new living check models a localhost WebSocket plus Imani's
physical address and requires `http://192.168.0.100:8080`.

```sh
PYTHONPATH=dashboard PYTHONDONTWRITEBYTECODE=1 \
  ~/.venvs/bopos/bin/python -c \
  'from osc_bridge import source_for_peer; print(source_for_peer("192.168.0.103"))'
```

Real Mac probe result: `192.168.0.100`.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m unittest -v tests.test_device_control_routing \
  tests.test_device_patch_override
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_device_patch_targeting.py
```

Passed 12/12 unit checks and 14/14 real-dashboard + simfleet browser checks.

The adjacent archived
`.loom/tied/distribution-workflow/verify_distribution_workflow.py` passed both
URL-routing assertions and finished 7/9. Its two failures are stale UI copy/DOM
assertions ("simulated UI removes byte distribution" and "real dropdown copy")
outside the changed backend route surface.

`git diff --check` passed. The running dashboard was not restarted, so adoption
of the code change awaits its next normal restart. No `.pd` file or Pi
Tailscale configuration changed.
