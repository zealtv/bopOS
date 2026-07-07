# Verification — 2026-07-07

Codex delegation was attempted (prompt in `codex-prompt.md`) but the run died
at "model at capacity" 3k tokens in, before writing anything — implemented by
hand instead (the design was fully specified, so this was cheaper than
retrying a saturated provider). All checks live on the laptop, loopback UDP,
pyOSC3 + python-osc via scratchpad PYTHONPATH.

## Unit checks — `test_assign_persistence.py` (30/30 pass)

```
PYTHONPATH=<pylib>:python:python/io:tools python3 .loom/threads/osc-schema-contract/assign-persistence.stitching/test_assign_persistence.py
```
Store (atomic write, no tmp artifacts, invalid/dotfile keys rejected loudly,
overwrite full-state, ephemeral RAM-only), boot resolution (persisted beats
seed beats −1), `/os/assign` (applies id/hostname/engine-`/id`/store/hb-wake;
uid mismatch untouched; idempotent), LAN `/os/store`+`/os/load` (typed
values, unicast to (src, 5550), missing key → legal empty), localhost
`/store`/`/load` for the engine path, simfleet persistence (override, ignore
for ephemeral, save round-trip).

Note: hb-identity's tied test needed a two-line amendment (its exact-dict
config assertions gained the `UPDATE_MODEL` default) — re-run, 24/24 pass.

## Live helper.py (real 5550 listener, PD-flag co-bind as before)

- Boot unregistered: `/hb … -1 … ` at 2 s. `/all/os/assign <uid> 55 <name>
  10 20 30 40` broadcast → **heartbeat with id 55 within 50 ms** (the
  hb_wake event), then 10 s cadence. `state/store/assignment` =
  `[55, "spectre", 10.0, 20.0, 30.0, 40.0]`.
- Kill helper, restart with **no dashboard traffic at all** → first beat is
  already id 55 (persisted assignment beat the absent bopos.devices row) —
  the standalone-after-network-removal mode, per the stitch instructions.
- Live assign used the laptop's current hostname so `set_hostname` no-ops —
  the real hostnamectl/hosts/avahi dance is the same code path `/config` has
  always run, but it was not exercised against this laptop on purpose.

## Live simfleet (the instructions' loop, verbatim)

Round 1: 2 devices `--unassigned 2 --ephemeral 1 --state-dir …` — both boot
−1 at 2 s; assigns to both MACs → immediate ack heartbeats at ids 12 and 13.
Round 2: fleet killed, dashboard listener gone, fleet restarted with the same
state dir → persistent device boots **id 12** on its first beat (slow
cadence); ephemeral device re-hellos at −1 every 2 s. State dir contains only
the persistent device's file.

Cadence note: an assign's new interval takes effect from the next scheduled
beat (one extra fast beat can fire after the ack) — idempotent, harmless,
same on the real node.

## Not verified — needs Bob or a live rig

- hostnamectl/avahi rename on a real Pi (code path unchanged from `/config`).
- Engine-side store/load through PD — blocked on the PD routing design
  (observation added to pd-edits-for-bob.md); the 7770 handlers are tested
  directly.
- Power-cut atomicity is by construction (tmp+rename), not fault-injected.
