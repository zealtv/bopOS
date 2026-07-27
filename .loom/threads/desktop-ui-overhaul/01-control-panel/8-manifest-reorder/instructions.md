# 8-manifest-reorder

Drag-to-reorder manifest entries in the Patch tab's manifest editor, so the
operator can reorder the control panel. Source: Bob's 2026-07-27 second
braindump (lore `2026-07-27-events-cues-and-global-controls-braindump`) —
"in the patch tab where you specify the manifest, it would be really useful
to be able to drag the parameters and events around to reposition them so we
can reorder the control panel."

Scope:

- The manifest editor (Patch tab) lets the operator drag parameter rows to a
  new position; the persisted manifest order changes accordingly, and every
  surface that renders manifest order (Control-tab panel, Device-tab control
  panel, facilitator view) follows it. Confirm first whether the control
  surfaces already render in manifest order — if they do, this stitch is
  editor drag UX + persistence only; if any surface sorts, fix it to honor
  manifest order as part of this stitch.
- Reordering is a manifest edit like any other: same save/dirty/fingerprint
  path, no new wire surface. Parameter *identity* (nested addresses) must be
  untouched by a move — order is presentation, not address.
- When event-kind entries exist (post-`44-event-plane`), they reorder the
  same way, but only **within** their section — the control panel keeps
  separate parameters and events sections (ruling in the same braindump), so
  cross-section drags are invalid. Build the constraint so it degrades to a
  no-op today when only params exist.

Verify: extend the nearest living Playwright journey (manifest editor) with a
drag reorder → saved manifest order changed → control panel renders the new
order. Mind gotcha (6): use `page.evaluate` scrolling, not auto-scroll waits.

Independent of `44-event-plane` — workable now for float/scalar params.
