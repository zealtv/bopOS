# northern-broadwalk-site-plan

**Status:** ready · data task, no hardware needed
**Goal:** Convert the Kite Choir Northern Broadwalk 52-position CSV into a loadable bopOS venue/site snapshot while preserving the router-relative coordinate convention.

## Input

`input/soh-northern-broadwalk-bopos-site-plan.csv` (in this stitch)
with provenance and conventions in the adjacent `README.md`.

## Requirements

- 52 unbound Seats, IDs `0..51`, names `Spool 00..Spool 51`.
- One element position per Seat from `(x_m, y_m)`; `element_index` is 0.
- Router/AP remains `(0,0)`, `x` plan-right, `y` plan-down. Do not silently translate the origin to
  make the current dashboard canvas convenient; if the venue schema needs a room/canvas offset,
  represent that separately and document it.
- Preserve the source CSV and `pole_height_m`; height is production context and must not be mistaken
  for a bopOS spatial coordinate.
- Keep group membership empty initially. Musical groups are section-specific and will be authored
  against this venue later.
- Validate IDs, names, finite coordinates, one position per Seat, counts (52 total; 24 × 4 m and
  28 × 3 m), coordinate bounds, and a visual comparison with the source working plan.
- Mark the resulting venue as provisional until compared with the issued SOH operational drawing.

## Acceptance

- A named Northern Broadwalk venue snapshot loads through the ordinary bopOS venue path without
  hand-edit repair.
- The Seats map visually matches the supplied plan and preserves router-relative values exactly.
- Automated or scripted validation covers the row/count/convention checks above.
- The remaining issued-drawing/on-site verification is stated explicitly; this stitch does not claim
  surveyed physical accuracy.

## Source

Kite Choir Brains lore `2026-08-28-northern-broadwalk-bopos-site-plan`.
