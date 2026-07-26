# 01-density-and-layout-design

Audit the current desktop application and propose a coherent app-wide density
and layout overhaul for Bob to ratify before implementation.

Cover the global header and primary navigation; Control, Show, Seats, Devices,
Patches, and Assets; shared panels, forms, tables, buttons, and the Monitor
dock. Identify the largest sources of wasted space and inconsistency, then
propose concrete values and patterns for:

- control height, horizontal/vertical padding, gaps, panel padding, and radii;
- typography scale and information hierarchy;
- workspace widths, columns, scroll regions, and use of the viewport;
- compact presentation of repeated actions, status, diagnostics, and metadata;
- desktop pointer/keyboard behavior while retaining accessible labels, focus,
  and suitable hit areas where touch remains relevant.

Use the tied Show compact-chrome variables and screenshots as evidence, not as
an automatic app-wide prescription. Check the current implementation at common
desktop widths and retain representative before/proposal mockups.

Deliver `audit.md`, a small token/pattern proposal, mockups for the major
workspace shapes, and an implementation split with focused regression
boundaries. Bring the decisions to Bob for ratification; do not implement the
overhaul in this stitch.
