# 67-repair-pass

**Goal:** fix the defects the October code review found, before cleanup and
refactoring build on top of them.

**Status:** new (2026-10-03). All children ready and independent.

Evidence and reproductions: `lore:2026-10-03-bopos-code-review-2026-10` (§ Bugs). The review's `addpatch` defect (B2)
is not here — it goes away with `68-remove-git-patch-route`.

## Stitches

1. `1-installation-load-wipe` — one bad reference empties the installation and
   the next save overwrites it. **Confirmed; do first.**
2. `2-device-enabled-honesty` — "disabled" reported while audio still plays on
   cards without a mixer. Needs a rig check.
3. `3-io-bridge-hardening` — LIS3DH ignores its address; io bridge errors go
   silent; no lock between write and poll. Absorbs `60-io-dispatch-silence`.
4. `4-contract-version-source` — `contract_version` hard-coded as 1.16 in
   three places.
5. `5-browser-tier-red` — five browser journeys have failed since before
   2026-09-03.

## Constraints

- Each fix lands with a test that fails before it.
- `tools/run-tests.sh fast` green per stitch; `browser` too once `5` is done.
