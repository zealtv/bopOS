# Handoff — dashboard UI review tied (2026-07-13)

State at handoff: the complete `dashboard-9-ui-review` branch is tied. The
technical dashboard now preserves unassigned identity drafts, pulses heartbeat
rows, leads with a full-width spatial overview, exposes technical master,
separates listener move/heading interaction, gives points coloured clipped
fields plus list selection, preserves moving-point position through edits, and
supports true-N numeric coordinates relative to a persisted visual room datum.
Dead Aloha dashboard/facilitator surface was removed. No stitch is claimed;
`patch-asset-sync/dist-1-contract-amendment` is next.

## Stitches tied this session

- `ui-0-sidebar-fixes`: implementation `3810cdf`, tie `546e7f7`
- `ui-1-layout-pass`: implementation `3f2280c`, tie `3c48146`
- `ui-2-spatial-map-pass`: implementation `a179c15`, tie `fddec96`
- `ui-3-position-precision`: implementation `4faafea`, tie `48ff5a9`
- `dashboard-9-ui-review` parent: record `0e480b1`, tie `11a0ced`

Each child retains `RESULTS.md`, a focused Playwright verifier, and (for
ui-1..3) a review screenshot under `.loom/tied/<stitch>/`.

## In-flight / waiting

No in-flight stitch. Existing waiting stitches and their hardware/decision
gates are unchanged; `./.loom/loom status` is authoritative.

## Recommended next stitch

Claim `dist-1-contract-amendment`. It freezes the ratified patch distribution
model as OSC contract v1.3 before node/dashboard/demo implementation. Continue
in the audited order: dist-1, dist-2, dist-3, dist-4, then d8-1..3.

## Decisions awaiting Bob

None from this session. Bob reviewed after ui-0..2 and asked the run to
continue. Listener visibility remains owned by d8-2; hostname-based naming
remains owned by dist-1/2 then d8-3.

## Gotchas and verification

- Headless Chromium requires execution outside the filesystem sandbox on this
  Mac; Bob explicitly pre-approved Chromium for the run.
- The focused child suites pass: ui-0 4/4, ui-1 10/10, ui-2 9/9, ui-3 9/9.
- Several older tied integration harnesses discover no simulator row with ID 1
  (or never receive their seeded declaration) and stop before relevant
  assertions. This is a stale harness/setup issue: current focused suites prove
  the changed paths, while low-level point checks passed 6/6. Do not treat the
  historical setup exception as a product regression.
- The room `origin` is deliberately a visual datum. Numeric display is
  `local_position - origin`; entry converts back before the unchanged assign
  wire path. Moving the datum does not move audio geometry.
- iPad/touch and installation hardware remain unverified.

## Usage at stop

- Codex weekly: 61%, resets `2026-07-20T01:42:13Z`.
- The available Codex meter reported no separate five-hour cap.
