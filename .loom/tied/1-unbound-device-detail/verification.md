# Verification

Date: 2026-07-26

## Focused checks

```sh
git diff --check
node --check dashboard/static/js/control-surface.js
node --check dashboard/static/js/dashboard.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  -m py_compile tests/verify_device_control_panel.py \
  tests/verify_control_surface_component.py
```

All passed.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_control_surface_component.py
```

Passed 11/11 checks. This includes facilitator All/Group/Seat rendering,
single-member Seat/Device value and running-automation presentation parity,
host-owned Device sends, both component hosts, and zero page errors.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_device_control_panel.py
```

Passed 16/16 checks. The verifier recreates Imani Silver as an online,
unbound `id=-1` physical record with `report`, `patches`, `assets`, and
`declared` null at selection time. It checks full detail rendering, assignment
and administration surfaces, disabled declaration-default controls with clear
provenance, zero content-message emission, the existing bound Device send,
pinned-patch schema selection, offline behavior, and zero page errors.

## Adjacent regressions

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_generator_drawer.py
```

Passed 38/38 checks across agreeing and mixed aggregate scenarios.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_control_tab.py
```

Passed 15/15 checks, including All/Group/Seat consumers and zero page errors.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  tests/verify_precision_param_input.py
```

Passed 13/13 checks, including precise shared-surface values and zero page
errors.

## Boundary

No real Pi or installation-LAN round-trip was attempted. This stitch is
UI-only: verification covers rendering and confirms that unbound Device
controls do not emit content messages. UID-scoped administration round-trips
and the macOS physical OSC route remain explicitly owned by
`2-macos-osc-routing-shutdown`.
