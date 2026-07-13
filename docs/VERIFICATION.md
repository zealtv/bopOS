# Verification matrix

Verification is proportional to the stitch. There is no single all-project test
command: each completed stitch retains its focused tests and evidence under
`.loom/tied/<stitch>/`.

Use `~/.venvs/bopos/bin/python` for project verifies. Dependency and Chromium
setup is documented in `CLAUDE.md` and `dashboard/README.md`. Set
`PYTHONPYCACHEPREFIX=/tmp/bopos-pycache` for compile/import checks launched from
stitch directories so generated `__pycache__` folders do not appear to Loom as
unresolved child stitches. Focused verifier scripts should also set
`sys.dont_write_bytecode = True` before importing repository modules.

| Change area | Minimum local verification | Stronger / integration verification | Hardware boundary |
|---|---|---|---|
| Python module or helper logic | Run the focused `test_*.py` or `verify_*.py` associated with the feature; compile every touched Python file with `python -m py_compile <files>` | Run nearby tied regression verifies that exercise the same wire plane | Report hardware as unverified unless run on a real node |
| OSC contract or node protocol | Add or update a browser-free `verify_*.py`; exercise the real helper where practical | Run the real dashboard and `tools/simfleet.py` on non-default ports; protocol changes must land in simfleet in the same stitch | Confirm broadcast, audio-engine delivery, or peripheral behavior on the rig when required |
| Dashboard backend / WebSocket state | Browser-free verify against the real `dashboard/server.py` and simfleet | Run the relevant Playwright dashboard regression | Verify discovery and control on the installation LAN before calling rig adoption complete |
| Dashboard or facilitator UI | Focused Playwright `verify_*.py` using the newest tied browser verify as the template | Run adjacent UI regressions, especially facilitator, spatial, patch-management, and meter surfaces affected by the change | Check iPad/touch interaction when the behavior is facilitator-facing |
| Clock sync and cue timing | `.loom/tied/sync-3-jitter-harness/verify_sync_measure.py` or the narrower sync verify for the changed layer | `tools/sync_measure.py --devices 5 --sync-skew-ms 40` | `tools/sync_measure.py --mode hardware --cues 8`; software spread is only a floor |
| Spatial terms / point decomposition | `.loom/tied/seam-3-points-node-side/verify_points_node_side.py` | Real dashboard + simfleet; recompute expected falloff from sniffed point frames | Audible confirmation awaits the documented PD receiver edits and a rig |
| Pure Data integration | Do not edit `.pd`; update `.notes/pd-edits-for-bob.md` with exact live spellings and expected behavior | Verify the Python/dashboard/simfleet side independently | Bob performs the PD edit and audible rig verification |
| Bash, boot, audio-board, or peripheral work | Static review plus the narrowest safe local check | Laptop rig where applicable (`bash/start-laptop.sh`) | Follow `docs/HARDWARE.md`; record board, OS, command, result, and limitations |
| Documentation or contract-only change | Check links, commands, terminology, and consistency with `CLAUDE.md` | If normative, inspect affected implementation and stitch instructions for drift | None unless the documentation asserts hardware behavior |

## Routine commands

```sh
# Current work state; do not claim a stitch merely to inspect it
./.loom/loom.sh status

# Manual dashboard smoke test, terminals 1 and 2
~/.venvs/bopos/bin/python dashboard/server.py
~/.venvs/bopos/bin/python tools/simfleet.py --devices 5

# Current provided-term regression examples
~/.venvs/bopos/bin/python .loom/tied/seam-2-master-term/verify_master_term.py
~/.venvs/bopos/bin/python .loom/tied/seam-3-points-node-side/verify_points_node_side.py

# Software clock-sync measurement
~/.venvs/bopos/bin/python tools/sync_measure.py --devices 5 --sync-skew-ms 40
```

## Stitch completion record

Before tying a stitch, retain inside its directory:

1. A focused verification script when behavior changed.
2. The exact commands run and pass/fail counts.
3. Relevant regression results.
4. An honest statement of anything not tested, especially hardware, macOS,
   browser/touch, audio, or pending PD work.

Test scripts must locate the repository by a marker or imported module path.
Tying moves their directory, so fixed `../..` assumptions are invalid.
