# seam-4 results

Implemented the ratified owner split for the facilitator surface:

- Patch manifests may mark a parameter with `"facilitator": true`; the
  validator requires a boolean and the facilitator renders only explicit,
  non-meter promotions alongside the existing volume control.
- `installation.json` owns `facilitator_commands`, defaults empty, filters
  unknown/duplicate entries, and persists the sanitized list with venue state.
- Allowlisted commands are fleet-wide and confirmation-gated. `update`,
  `reboot`, and `shutdown` require a 1.2-second hold; a short press is a no-op.
- The default simfleet manifest subject is `backing`, promoted through the
  real `patches/default/bopos.patch.json` served verbatim by simfleet.

## Verification

`~/.venvs/bopos/bin/python verify_facilitator_promotion.py` — **13/13 pass**
against the real dashboard, simfleet, and headless Chromium:

- manifest flag type and missing-allowlist defaults;
- promoted/unpromoted/volume/meter separation;
- default-empty and sanitized command allowlists;
- short destructive press rejected;
- raw `p/backing=0.33` observed at simfleet;
- confirmed restart-engine and held update observed once per simulated device;
- sanitized allowlist persisted.

`python -m py_compile` passed for `python/manifest.py`, `dashboard/state.py`,
`dashboard/server.py`, and `tools/simfleet.py`. `git diff --check` passed.

Adjacent historical Playwright suites were also run. Their substantive checks
passed. Their generic `input[type=range]` counts now fail because promoted
ranges intentionally join the volume range, and the old facilitator suite's
master×gain wire assertions predate seam-2's removal of framework composition.
The new verify uses named parameter selectors and asserts raw patch values.
Historical tied scripts and screenshots were left unchanged.

## Not verified

Touch interaction on a physical iPad and commands against a real fleet remain
hardware/rig-adoption checks. No Pure Data changes are required by this stitch.
