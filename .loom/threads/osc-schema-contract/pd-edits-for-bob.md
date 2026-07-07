# PD edits for Bob

Running list of `.pd` changes the contract implementation needs. Agents append
exact specs here as stitches hit them (per HANDOFF.md); Python-side work never
waits on these — aliases keep both spellings working.

## Observations (no edit requested yet, but you should know)

- **2026-07-07, found while building simfleet:** the heartbeat's version report
  is dead wiring. In `pd/bopos.osc.pd`, the metro reads `value version`
  (obj ~129 737), but nothing anywhere writes that value: the patch loadbang
  `version 1` (`patches/default/main.pd`) goes into osc-in → `route version` →
  `s version` — and there is no `r version` (and `send` doesn't set `value`).
  So every deployed device reports `/rpt <id> version 0` regardless of patch.
  No fix requested: `hb-identity` replaces version reporting (version moves into
  `/hb` as a string from helper.py). Mentioned so a "v. 0" on the dashboard
  doesn't send anyone debugging the wrong thing.
- Same file: `route-by-id` boots matching selector **−1** while `list prepend 0`
  reports id **0** — an unconfigured device reports as 0 but only answers −1.
  Goes away with `assign-persistence` (contract uses −1 consistently).
- `process-helper-messages` route list omits `checkout`, so `helper checkout`
  never reaches helper.py from the LAN. Contract §7 keeps `/os/checkout`, so
  either the route gains it there or the `/os/*` migration obsoletes the whole
  route list — flagging so it isn't copied forward as-is.

## Requested edits

### 1. Forward `restart-engine` to helper.py (from node-contract-fixes)

In `pd/bopos.osc.pd`, subpatch `process-helper-messages`:

- Add `restart-engine` to the route list:
  `route reboot shutdown update getsamples addpatch patch pullpatch config`
  → `route reboot shutdown update getsamples addpatch patch pullpatch config restart-engine`
- Give the new outlet the same treatment as `reboot`: `t b b` → left bang into
  `delay 500` → `msg 1` → `oscformat restart-engine` → the subpatch outlet
  (netsend to helper on 7770). The right bang of `t b b` can `s restart-engine`
  internally if patches want a fadeout hook, mirroring `s reboot`.

helper.py already has the `/restart-engine` handler (stops pd+jackd via
pidfiles, re-runs `bash/start-engine.sh`); until this edit lands, the verb is
simply unreachable from the LAN — nothing breaks.

Test after editing: `helper restart-engine` to a device on the laptop rig →
expect `/rpt <id> helper-reply restart-engine` on 5550, engine restarts,
helper/io processes untouched.
