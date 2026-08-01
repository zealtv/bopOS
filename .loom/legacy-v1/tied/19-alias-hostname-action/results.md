# Alias-derived hostname action — results

The selected Physical device now exposes a **Set hostname** action derived on
the Dashboard host from its current alias (`Finn Jet` → `finn-jet`). The
browser supplies only the exact device UID. A successful node receipt updates
the displayed hostname; pending, current, and retry states remain explicit.

The node uses a validating root-owned helper through `sudo -n`. Existing Pis
need one manual `sudo bash/provision.sh` run to install the helper and updated
sudoers policy. Routine **Update bopOS** intentionally cannot change this
root-owned boundary.

## Verification

Passed on 2026-07-16:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/19-alias-hostname-action/verify_alias_hostname.py
# 10/10

node --check dashboard/static/js/dashboard.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/device_aliases.py dashboard/server.py dashboard/osc_bridge.py \
  python/bopos.py tools/simfleet.py tools/audition.py
bash -n systemd/bopos-set-hostname bash/provision.sh bash/install-power-control.sh
/usr/sbin/visudo -cf systemd/bopos-power.sudoers
# parsed OK
git diff --check
```

The focused verifier exercises the real Dashboard, a two-node simfleet, and
Chromium, plus the actual node helper function with the privileged subprocess
mocked at its narrow boundary. It proves server-side derivation, exact-UID
isolation, simulator persistence, terminal success/error receipts, and UI
pending/current/retry behavior. Visual evidence is
`alias-hostname-action.png`.

No `.pd` file changed. The helper was not installed or exercised as root on a
real Pi, and hostname propagation on the installation LAN was not tested.
