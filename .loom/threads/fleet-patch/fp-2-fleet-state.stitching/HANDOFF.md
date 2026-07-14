# fp-2 handoff — 2026-07-14, usage window ended

Slice 1 is DONE and committed: `dashboard/state.py` carries the full fp-2
state model — `patch_badge()` (precedence unit-checked 10/10: unset >
unknown > switching > missing > mismatch > stale/stale_unverified > current),
`clean_fleet_patch`, `stage_fleet_patch` (previous rotates only on name
change), seat `patch` deleted from clean_seat/_import_seed, fleet_patch in
durable()/load/venues, `simulation["patch"]` read-through on load. Nothing
consumes it yet; the tree is coherent and all prior verifies unaffected.

Remaining slices (spec: `.loom/tied/fp-0-design-proposal/proposal.md` §3-§5
and this stitch's instructions.md):

2. **server.py wiring** — route the sim switch path (server.py:208,
   618-631) through `state.stage_fleet_patch`; add WS commands
   `set_fleet_patch` (validate host manifest, capture catalog fingerprint,
   stage, converge-then-switch: fetch to online non-current real devices
   respecting the tombstone rule osc_bridge.py:506-517, then per-device
   `/id/os/patch` as the existing flow at server.py:~198-232),
   `revert_fleet_patch` (re-stage previous via same flow),
   `retry_fleet_patch` (one device: re-fetch missing/stale, re-switch
   mismatch). Keep per-device switch_patch working (fp-3 removes its UI).
3. **Badge over WS** — attach `patch_badge(device, desired)` to device
   broadcast payloads (fleet_patch itself already rides state.public()).
   Resolve `desired` fingerprint against the live host catalog at
   derivation time.
4. **verify_fp2_fleet_state.py** in this stitch dir (repo by marker,
   ~/.venvs/bopos venv, browser-free against simfleet): persistence +
   previous rotation; old state file drops seat patch; badge unit cases;
   set_fleet_patch happy path → all `current`; offline stays `unknown`;
   induced stale (edit host file post-convergence) + operator retry;
   revert.

The badge precedence unit check from this session (inline, passed) is worth
folding into the verify as-is.
