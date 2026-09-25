# Handoff — engine-boundary thread complete (2026-07-12)

State at handoff: working tree clean, main pushed (`Point CLAUDE.md at
contract v1.2` is HEAD), loom has no claims.

## What landed this session

- **boundary-5 tied**: `python/runcontext.py` (seed ≤6 digits + opaque
  run-id), atomic launch delivery (`bopos-context` bus for PD / `BOPOS_*` env
  for others), SC starter retries `/config` and binds `BOPOS_ENGINE_PORT`,
  shared `python/relay.py` shaping for helper+audition (audition's legacy
  `/identify` and `/os/mute` relays fixed). 68-check verify in the tied
  stitch; hardware run on bop000 recorded there.
- **boundary-6 tied, goal tied**: `docs/OSC-CONTRACT.md` is **v1.2** (new
  §4.2 engine surface, run context, civil-time amendment, one-shot
  `/os/probe`, clean break — see the stitch's `results.md` for the full
  change list). `helper.py` → `bopos.py` renamed with all live references
  updated; tied verify suites retargeted (`import bopos as helper`).
- **bop000 deployed**: at current main; `bopos-helper` unit re-copied to
  `/etc/systemd/system/` (it's a copy, not a symlink — remember this on any
  future rename), running `python/bopos.py`; ping/identify verified from the
  Mac. Access: `ssh -i ~/.ssh/id_ed25519_spectre pi@192.168.0.101`; sudo
  needs Bob. A stash `bop000 bench edits pre-boundary-5` and
  `systemd.local-copy/` were left on the Pi from reconciling bench edits.

## For the next session

- **Unblocked, ready to claim**: the three engine-boundary-adoption waiters —
  `audition-1c`, `audition-2a`, `friction-1a` (claim a `.waiting` stitch to
  resume it). Then the loose ends: `friction-0-docs`, `zero-0-measure-kit`,
  `dashboard-5-position-precision` (deliberately last).
- **Do NOT start `sample-distribution` (samples-0/1/2) autonomously** — Bob
  wants a design dialogue first (2026-07-12).
- **Pre-existing red tied suites** (fail identically at pre-thread `2dc98f5`;
  detailed in tied `boundary-6-contract-v12-and-renames/results.md`):
  hb-identity (3 checks), node-contract-fixes (pyOSC3.SENT), seam-3
  points-node-side (StopIteration). boundary-2's verify is superseded by
  design (expects `pd/bopos.osc.pd`). A small housekeeping stitch could
  green or retire them.
- Not exercised: `sclang` launch of the SC starter (text-verified only);
  audible identify chirp on bop000.
