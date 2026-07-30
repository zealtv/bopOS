# 02-app-wide-rollout-design

*(Renamed from `01-density-and-layout-design` on 2026-07-27: Bob put the
control-panel UI first — `01-control-panel` defines the design language on
one surface; this stitch turns it into the app-wide rollout strategy.)*

After `01-control-panel` is tied: audit the rest of the desktop application
and propose how the ratified control-panel design language rolls out
app-wide, for Bob to ratify before implementation.

Start from the control-panel language's extrapolated rules (compactness,
grayscale + cyan semantics, one-line controls, click-to-type precision,
visible generator state) rather than inventing a parallel system. Cover the
global header and primary navigation; Control, Show, Seats, Devices, Patches,
and Assets; shared panels, forms, tables, buttons, and the Monitor dock.
Identify the largest sources of wasted space and inconsistency, then propose
concrete values and patterns for:

- control height, horizontal/vertical padding, gaps, panel padding, and radii;
- typography scale and information hierarchy;
- workspace widths, columns, scroll regions, and use of the viewport;
- compact presentation of repeated actions, status, diagnostics, and metadata;
- desktop pointer/keyboard behavior while retaining accessible labels, focus,
  and suitable hit areas where touch remains relevant.

The standalone facilitator surface keeps its separate tablet-first
constraints. Use the tied Show compact-chrome variables and screenshots as
evidence, not as an automatic prescription. Check the current implementation
at common desktop widths and retain representative before/proposal mockups.

Deliver `audit.md`, a token/pattern proposal, mockups for the major workspace
shapes, and an implementation split with focused regression boundaries. Bring
the decisions to Bob for ratification; do not implement the overhaul in this
stitch.
