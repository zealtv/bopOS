# 1-reproduce-diagnose

Reproduce the freshly-flashed-Pi-goes-unresponsive-on-patch-send bug and pin the
exact point of failure. This stitch ends with a named cause and a `2-fix` stitch
created from it — not with a speculative patch.

## Reproduce

- **Simfleet first** (no hardware): stand up a *fresh* node — empty
  `assets/`, no prior active patch, cold fingerprint cache — and drive a fleet
  patch send at it. Watch the heartbeat on 5550 and command surface on 6660
  across the send. If a clean simfleet node reproduces the quiet, the bug is in
  `bopos.py`/`fetcher.py`, not PD.
- **Dev Pi** `bop000` if simfleet won't show it (see memory `bop000-dev-pi-access`
  — `ssh -i ~/.ssh/id_ed25519_spectre pi@192.168.0.101`; confirm reachable this
  session; sudo needs Bob). Reflash is Bob's; a `git clean`/wiped `assets/` +
  cleared active patch approximates "fresh" without reflashing.

## Diagnose

- Capture *where* it stops: does the heartbeat thread die, block, or keep
  beating while the node just stops acting on commands? Does `bopos.py` still
  have a live process (SSH `ps`, check its log) or did it crash?
- Trace the patch-send path end to end: relay/Dashboard push → node receive →
  `fetcher` patch+asset install → cache warm → engine (re)launch. Add timing/log
  points; find the blocking call or the exception that isn't caught.
- Prime suspects to confirm or clear: no-timeout `urllib` fetch against an
  unreachable/slow source; `asset_warm_lock` contention or a cold-cache warm
  that blocks the OSC loop; a first-sync-only code path (empty assets, missing
  active_patch).
- **Cheap hedge (2026-07-23 assessment):** the guard-rot sweep left several
  patch-path guards red — `dist-2-node-side`, `patch-switch-lifecycle`,
  `fp-2-fleet-state`. Assessed as stale (version/message-list/compat drift;
  behavioral fetch assertions still pass), **not** the node bug — but they cover
  exactly this code, so skim their failures here in case a real regression is
  hiding among the drift. Do not fix them (that's `27-tied-guard-rot`); just
  read them as evidence.

## Deliverable

- `diagnosis.md` in this stitch: the exact cause, the evidence, and whether the
  fix is Python-only or needs a Bob PD edit.
- Create `2-fix` (sibling) with the concrete fix named. If the cause is a Bob PD
  edit, record it in `.notes/pd-edits-for-bob.md` and mark `2-fix` `.waiting` on
  Bob.
- Leave the reproduction harness (simfleet scenario / script) in the stitch so
  `2-fix` can prove the repair and ship it as a guard.
