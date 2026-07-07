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

### 2. Identify chirp hook (from hb-identity)

`/os/identify` (contract §6: locate a box on install day) is handled by
helper.py, which asks the engine to make itself known by sending `/identify`
to PD on **6661** (the existing helper→PD reply port). Wanted in
`pd/bopos.osc.pd` (or the OS layer patch of your choice):

- Route `identify` off the 6661 netreceive → make an audible chirp (a short
  test tone through the patch output is ideal — it proves the whole audio
  chain) and/or `s identify` so patches can add their own flash/print.
- Until this lands, `/identify` on 6661 just rides PD's existing
  forward-everything-to-5550 path (an inert `/rpt` on the wire) — harmless,
  nothing breaks; the box only fails to chirp.

Test after editing: `/all/os/identify` broadcast to 6660 → every running box
chirps; `/all/os/identify <uid>` → only the box with that MAC chirps.

### 3. Retire PD's own heartbeat + aloha emitters (from hb-identity)

helper.py now sends the contract heartbeat
(`/hb <uid> <id> <version> <engine-alive> [rssi]`) straight to 5550 — that is
the liveness signal, and it deliberately survives PD/engine death. PD's old
emitters are now redundant wire noise, in `pd/bopos.osc.pd`:

- The metro that sends `/rpt <id> hb` + `/rpt <id> version …` (the `value
  version` it reads is dead wiring anyway — see Observations above).
- The loadbang → `delay 1000` → `aloha` boot announce, and the `aloha` command
  reply (§5: announce is absorbed by the fast heartbeat; locate is
  `/os/identify`).

No urgency: both old and new messages coexisting is the expected migration
state (simfleet's `--legacy-reports` models exactly this). Remove them when
the dashboard no longer reads `/rpt … hb` (dashboard-1 speaks contract v1
from birth, so: any time after dashboard-1 replaces DASHBOARD.pd for daily
use).

Test after editing: on 5550 expect `/hb …` every 10 s per box and **no more**
`/rpt <id> hb` / `/rpt <id> version` / boot `aloha`.
