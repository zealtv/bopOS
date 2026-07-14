# Patch switch lifecycle results

`/os/patch <name>` now switches only the audio engine stack. The OS, helper,
dashboard connection, and I/O bridge remain online.

## Implementation

- A real node validates the target and updates an inactive Git target before
  interrupting audio, then stops the engine stack, atomically selects the patch,
  starts the replacement, and returns from the provisioning callback only after
  engine liveness is confirmed.
- Failed replacement startup stops any partial process, restores
  `active_patch.txt`, and relaunches the prior patch.
- `hb_wake` exposes the engine-down/up transition without waiting for the normal
  heartbeat interval.
- Simfleet models the same helper-alive / engine-restarting lifecycle and sends
  `/os/rev` after its replacement engine is alive.
- The dashboard shows `Switching…`; the confirmation accurately says the device
  remains online. On `/os/rev`, it clears the phase and requests `/os/patches`,
  `/os/params`, and `/os/report`. An 8-second query is retained as a fallback for
  a lost UDP receipt.
- The OSC contract and dashboard/I/O lifecycle documentation now describe the
  engine-only boundary.

## Verification

- `verify_patch_switch_lifecycle.py`: **10/10 passed** — real selection,
  stop/start-only command sequence, awaited launch, rollback, simfleet
  engine-only lifecycle, post-start receipt, dashboard phase clearing, all
  three refresh queries, UI copy, and contract copy.
- Managed distribution lifecycle: **9/9 passed**.
- Managed distribution Chromium UI: **5/5 passed**.
- Managed simulation lifecycle: **9/9 passed**.
- Managed cue/point controls: **9/9 passed**.
- Existing node distribution suite: all production-node checks passed. Its one
  pre-existing stale sim-only check still requests `patch:default` although
  simfleet's active patch is `demo-pd`; this mismatch is unrelated to the
  engine-only switch implementation.
- Python compilation, dashboard JavaScript syntax, and `git diff --check` pass.

## Hardware boundary

The new lifecycle has not yet been deployed to or exercised on bop000. No `.pd`
file changed. Bob's next test is a real switch between already-installed
patches, checking that the Pi stays online, audio returns, and the dashboard
parameter controls change to the selected manifest.
