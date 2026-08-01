# Seat identity leak results

## Outcome

- Binding a device no longer copies its technical hostname into an empty or
  default seat name.
- Bound Dashboard cards resolve their primary identity from the seat and show
  `<seat name> · ID <seat id>`. Hostname and uid remain secondary technical
  identity. Virtual cards resolve through `seat_id` using the same rule.
- Dashboard and standalone compatibility surfaces label presets as **Seat
  presets**; the save prompt explicitly says it captures seat params + master.
- Full-state selection reconciliation follows a newly bound device into its
  seat, clears the stale device on unbind, and clears both selected values when
  the selected seat is removed.

## Verification

Passed:

```sh
node --check dashboard/static/js/dashboard.js
node --check dashboard/static/js/facilitator.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile .loom/threads/ui-tabs/tabs-3-next-sweep/03-seat-identity-leaks.stitching/verify_seat_identity.py
```

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/threads/ui-tabs/tabs-3-next-sweep/03-seat-identity-leaks.stitching/verify_seat_identity.py
```

Result: **10/10 passed** in headless Chromium against the real dashboard and
OSC discovery/report path. Covered default-name preservation, bound card
identity, technical secondary identity, preset wording, bind/unbind/rebind/
remove selection state, browser errors, and clean shutdown.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/tied/tabs-1-skeleton/verify_tabs_skeleton.py
```

Result: **20/20 passed**.

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/tied/01-simulation-transition-coherence/verify_simulation_transition.py
```

Result: **7/7 passed**.

```sh
git diff --check
```

Result: passed.

## Boundaries

This stitch corrects identity and selection behavior only. The wider
Seat/Device ownership, reindexing, unbound administration and curated device
alias decisions remain in accepted stitches 06–09 and 14. No `.pd` file
changed. No hardware rig, audible engine, installation LAN, or iPad/touch
browser was tested.
