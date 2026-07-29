# 07-control-device-ui

The provisional preset row goes live on the Control tab and Device panel —
and comes **off** the standalone facilitator. **Needs 06 tied.** Parallel
with 08.

Authority: proposal §1/§3, addendum §7/§9-Q4,
`.loom/tied/3-addendum-review/review-2.md` F8. The designed-but-inert row is
`dashboard/static/js/control-surface.js:252-277` (`presetRow`, from tied
stitch `desktop-ui-overhaul/01-control-panel/7-preset-slot`); its anatomy
(patch name, dropdown, `new`/`save`/`del`) is the ratified control-panel
design — land into it, don't redesign it.

## Scope

- **Row goes live** on the embedded Control tab (All/Group/Seat cards) and
  the Device panel. The presets listed are those of the patch that owns the
  card's schema (fleet patch; a pinned device's own patch — the 06 service
  answers this). Selecting a preset applies through the 06 core; the apply
  report renders as **one compact line with a disclosure**, never a modal.
- **Provenance + dirtiness**: the dropdown shows the applied preset from the
  06 per-seat provenance projection (all seats agree → name, else mixed —
  the panel's existing mixed idiom); derived-dirty renders as the `Dawn *`
  asterisk; schema drift renders inline on the row, non-blocking.
- **Save** (`save`/`new`): captures via the 06 capture function. Default is
  capture-everything with per-row include/exclude affordances. **Mixed
  params on an aggregate card must be visibly marked as
  omitted-as-mixed before commit** (F8) — a silent sparse omission surprises
  on the next apply. Overwrite goes through the store's revision token; a
  conflict surfaces as a refresh-and-retry, not a silent clobber.
- **Device panel**: lists the pinned patch's presets; **save is disabled
  while the device is offline** (F8 ruling — apply stays legal, capturing
  from a device you cannot hear does not). The panel is already
  visible-but-disabled offline; follow that pattern.
- **Facilitator removal** (Bob's Q4 ruling: *no preset affordance at all* on
  the standalone facilitator/iPad surface): remove the preset row from the
  facilitator host of the shared `ControlSurface` (rendered by
  `facilitator.js`) — removed, not inert. This **supersedes decision 1 of
  tied stitch `7-preset-slot`** ("the row is per panel, not per privileged
  card"); record the supersession by name in this stitch's `decisions.md`
  per CLAUDE.md's interim rule. Parallel: `04-event-fire-affordance` — an
  iPad fires, it does not configure.

## Out of scope

The patch editor's save/recall (08), capture-as-step (09), retiring the old
facilitator preset shelf (10 — it still exists until then; do not break it).

## Verify and tie

Playwright journeys extending the nearest living `tests/verify_*.py`
(simfleet on non-default ports, repo-by-marker, teardown). Mind the CLAUDE.md
gotchas, especially (15) the Control surface is an iframe — use
`page.frame_locator("#dashboard-live-view")` — and (16) wait on the handler
binding, not the element, before dispatching. Cover: apply + provenance +
asterisk after a nudge; mixed card; save round-trip incl. include/exclude
and the omitted-as-mixed marking; revision conflict; facilitator page has no
preset row. `tools/run-tests.sh browser` and `fast` green. Decisions
(incl. the named supersession) in `decisions.md`.
