# patch-and-install-mgmt — verification

Date: 2026-07-08, dev laptop, loopback (real dashboard + real simfleet,
headless Chromium).

## What ran

`verify_patch_install.py` — 9/9 PASS:
- the device Patch panel shows the current patch from `/os/report`
- **Switch** sends `/os/patch <name>` (simfleet logs `os/patch wind_chimes`),
  the `/os/rev` receipt updates the Converged line, and after the simulated
  reboot the refreshed report shows the new patch
- **Add from GitHub** sends `/os/addpatch <user> <repo>` (simfleet logs it)
- **Pull latest** sends `/os/pullpatch` (simfleet logs it)
- Framework update reuses the existing per-device / Update-All actions with
  the version + `/os/rev` convergence already surfaced (no new code)
- **Venue save** writes `installations/<name>.json` and lists it; **load**
  replaces the device map and restores the saved room bounds (verified by
  changing the room to 25 m, loading the venue, and seeing 10 m return)

Screenshot: `01-patch-panel.png`. Sibling suites (spatial-map,
discovery-assign) re-run green after the server/state changes.

## Test-harness gotcha found (not a product bug)

- A global auto-accept dialog handler swallowed the venue "Save as…" prompt
  with an empty string; the test now uses one type-aware handler (prompt →
  name, confirm → accept).

## Not covered (needs a real rig / Bob)

- Real `/os/patch` on a Pi: git pull of the patch repo + reboot into it; real
  `/os/addpatch` cloning from GitHub (needs network + a real repo).
- Broadcast (`broadcast to all`) patch switch across a real multi-node fleet.
- Loading a venue whose devices are a different set than those currently
  heartbeating (partial overlap is handled in code; not stress-tested live).
