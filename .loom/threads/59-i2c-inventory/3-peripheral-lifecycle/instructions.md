# 3-peripheral-lifecycle: manifest modules

**Status:** after `1`
**Goal:** modules are declared in the manifest, created by the framework, and
describe their own inputs and outputs.

Spec: `../0a-io-design-review.tied/proposal.md` (ratified 2026-10-04; Bob's words in `rulings.md`). Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit. Wire changes are ratified as written in proposal §8; write the matching contract text and §15 row as each piece ships.

- `io_modules` in the manifest (name, type, address, optional), with a
  section in the Patches-tab manifest editor (proposal §3).
- At engine start, `bopos.py` has the bridge create each declared module;
  devices report presence. **Transition:** a patch-side `create` matching a
  declared module is a successful no-op; a conflicting one is `create-failed`.
  Removing patch-side creates is Bob's Pd edit (`64`).
- Writes: last write wins (one engine per device).
- **Driver descriptions** (proposal §5): each driver in `python/io/` declares
  its inputs (channels, units, ranges) and outputs (commands, args). The
  dashboard reads them from the host's copy of the drivers.

## Defects to fix (carried over; they exist with or without a UI)

1. **Failed creates are silent.** Fixed by `1` relaying errors; verify here
   end to end (wrong type, wrong address: Bob's 2026-08-05 case).
2. **Read errors log the wrong message, twice.** Pulling a LIS3DH logs
   `Error reading from LIS3DH at address 0x19` and then a `TypeError`
   (`a bytes-like object is required, not 'float'`) from inside the failure
   path. It should be one line: peripheral, address, "the bus didn't answer".
   It doubles the log rate (~5.7 MiB/hour). Check the other `io_*.py`
   drivers for the same shape.
