# Bash script staleness classification

| Script | Invoked by | Status | Note |
|---|---|---|---|
| `checkout.sh` | NONE FOUND | LIVE | Conservative classification: standalone branch-convergence utility (`bash/checkout.sh:2-3`); OSC checkout now performs convergence in-process (`python/bopos.py:1528-1536`), but this is not sample-era code. |
| `install-power-control.sh` | `bash/provision.sh:16` | LIVE | Installs and validates the privileged-control sudoers policy during provisioning (`bash/install-power-control.sh:34-36`). |
| `provision.sh` | `docs/INSTALL.md:82`, `docs/INSTALL.md:91`, `docs/INSTALL.md:145` | LIVE | Documented one-time/manual privileged provisioning step (`docs/INSTALL.md:85-92`). |
| `pull_active_patch.sh` | `python/bopos.py:1681`, executed at `python/bopos.py:1684` | LIVE | Implements the `/os/pullpatch` lifecycle path and returns a reboot-bearing result (`python/bopos.py:1677-1695`). |
| `rc.local` | Installed as `/etc/rc.local` by `bash/provision.sh:18` | LIVE | Current boot entry; starts the stack as `pi` (`bash/rc.local:20`). |
| `restart.sh` | NONE FOUND | LIVE | Conservative classification: generic manual full-stack helper composing `stop.sh` and `start.sh` (`bash/restart.sh:2-4`), with no sample-era behavior. |
| `start-engine.sh` | `bash/start.sh:81`; `python/bopos.py:378`, `python/bopos.py:1590`, `python/bopos.py:1596-1599`, `python/bopos.py:1742`, `python/bopos.py:1747`; manual path at `docs/HARDWARE.md:52-54` | LIVE | Used by boot, asset replacement, patch switching, and `/os/restart-engine`. |
| `start.sh` | `bash/rc.local:20`; `bash/restart.sh:4` | LIVE | Primary boot-time full-stack entrypoint (`bash/start.sh:64-81`). |
| `stop-engine.sh` | `bash/stop.sh:7`; `python/bopos.py:363`, `python/bopos.py:1589-1592`, `python/bopos.py:1741`, `python/bopos.py:1747`; manual path at `docs/HARDWARE.md:52-54` | LIVE | Targeted engine shutdown used by fetch replacement, patch switching, and restart-engine lifecycle paths. |
| `stop.sh` | `bash/restart.sh:3`; documented diagnostic invocation at `python/io/rssi_monitor.py:11-12` and `python/io/rssi_monitor.py:49` | LIVE | Manual full-stack shutdown remains useful; only its former broad `pkill` behavior is described as retired (`docs/OSC-CONTRACT.md:578-580`). |
| `update.sh` | Manual invocation documented at `docs/INSTALL.md:136-137`; prompted after provisioning at `bash/provision.sh:20` | LIVE | Manual convergence check; OSC Update bopOS uses equivalent in-process convergence (`python/bopos.py:1443-1496`, `python/bopos.py:1499-1504`). |

## Safely removable

None.

The only scripts with no caller/reference outside themselves are:

- `checkout.sh`: branch-selection/convergence code, not sample-download code (`bash/checkout.sh:2-3`, `bash/checkout.sh:50-62`).
- `restart.sh`: a generic stop/start wrapper, not sample-download code (`bash/restart.sh:2-4`).

Therefore neither meets the requested conservative removal threshold of both zero references and clear sample-era provenance.

## Lingering sample-download references in `bash/`

No `gdown`, `getsamples.sh`, or `SAMPLEPACKSURL` references were found.

The only `samplepacks` references are compatibility cleanup executed by `start-engine.sh`:

- Retired compatibility-path comment: `bash/start-engine.sh:62`
- Legacy path variable: `bash/start-engine.sh:65`
- Remove legacy symlink if present: `bash/start-engine.sh:66-67`
- Remove empty legacy assets directory: `bash/start-engine.sh:69`

These references clean up old state; they do not implement the retired download pipeline.