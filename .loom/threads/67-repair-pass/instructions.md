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

Added 2026-10-05 from `lore:2026-10-05-bopos-review-core-libs` (74/1):

12. `12-manifest-boundaries` — CLI quoting (high), malformed values raise,
    unwireable numbers validate.
13. `13-generator-correctness` — explicit-start loops, missed int crossings,
    unbounded fade work (high).
14. `14-point-boundaries` — malformed point input throws or clears; finished
    paths never go quiet.
15. `15-store-temp-files` — one key's write deletes another key (high).
16. `16-file-fetch-walk` — `file:` fetch follows source symlinks.

Added 2026-10-05 from `lore:2026-10-05-bopos-review-install-services` (74/3):

17. `17-usb-service-hardening` — root USB unit runs a pi-writable script
    (high); ignored partition's stop unmounts the active stick.
18. `18-engine-launch-failures` — launcher exits 0 after required steps fail.
19. `19-node-process-ownership` — daemon/IO crashes unsupervised; stale PIDs
    kill unrelated processes; dead helper unit and restart wrapper.

Added 2026-10-05 from `lore:2026-10-05-bopos-review-frontend` (74/2):

20. `20-remote-hold-cancel` — a re-render mid-hold lets Remote reboot fire
    after release (high).
21. `21-module-panel-sync` — reconnect and late-inventory gaps in module panels.
22. `22-spatial-cancelled-drag` — pointercancel leaves the map dragging.
23. `23-control-listener-hygiene` — stale generator gates, leaked listeners.

Added 2026-10-05 from `lore:2026-10-05-bopos-review-show-model` (74/4):

24. `24-show-number-boundary` — one bad number in a show file stops the
    dashboard (high); edits drop sockets; coerced, unbounded args.
25. `25-show-playback-consistency` — ghost "playing" steps; a 30k/s repeat.

## Constraints

- Each fix lands with a test that fails before it.
- `tools/run-tests.sh fast` green per stitch; `browser` too once `5` is done.
