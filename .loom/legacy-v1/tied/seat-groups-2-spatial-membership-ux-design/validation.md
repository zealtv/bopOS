# Validation record

## Automated browser study

Command run from the repository root:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/seat-groups/seat-groups-3-delivery/\
seat-groups-2-spatial-membership-ux-design.stitching/verify_prototype.py
```

Result: **7 focused checks passed**:

- one-group focus;
- four-group non-blended overlap;
- explicit fifth-group limit feedback;
- complete selected-Seat membership disclosure;
- clear and empty-group states;
- Seats-first/sidebar hierarchy plus eye/eye-off state and accessible actions;
- collapsed Groups summary retaining the active overlay count/state.

The first sandboxed Chromium launch exited with `SIGTRAP` before opening a page.
The same focused verifier passed when Chromium was permitted to run outside the
filesystem sandbox. This was an environment launch failure, not a failed UX
assertion.

## Visual inspection

Inspected `visual-study.png` after the passing browser run. It shows Seat 3 in
all four groups with four distinct rail positions/patterns, Front row focused,
other comparison rails muted, existing green element fill intact, white Seat
selection intact, a complete tooltip, and the fifth-group limit message. The
sidebar now visibly starts with Seats, roster, and Seat detail; Groups follows
as a subordinate disclosure. Open-eye buttons show the four visible layers and
the empty hidden group has an eye-off button.

`visual-study-empty.png` records the explicit empty-group focus state.
`visual-study-collapsed.png` records the quiet collapsed Groups summary while
the active map legend/rails remain visible.

## Visibility and hierarchy research

Reviewed current primary sources and recorded direct links, attribution, and
license implications in `proposal.md`:

- Figma's official Layers visibility help: eye is open for visible and closes
  for hidden layers. This is the closest conceptual convention.
- Microsoft Edge's native password reveal documentation: eye/slashed-eye is a
  familiar visibility pair, but password controls can express action rather
  than layer state; the proposal explicitly avoids importing that ambiguity.
- Material accessibility guidance: native boolean semantics, concise action
  labels, meaningful icon labels, contrast, and 44 px touch targets.
- Lucide's official `eye`/`eye-off` sources and ISC license; Material Symbols
  (Apache 2.0) and Fluent System Icons (MIT) as suitable alternatives.

Local dependency inspection found no dashboard vector icon system, icon font,
JavaScript package manifest, or reusable SVG component. The recommendation is
therefore two attributed inline SVGs rather than a new runtime dependency.

## Source consistency review

Reviewed the ratified Seat-group proposal, current Seats markup, `spatial.js`,
and current dashboard styling. The proposal deliberately preserves:

- group membership on Seats rather than devices/elements;
- canonical group identity as display name plus `g<id>`;
- element-index fill colour;
- current selected/offline/simulated/crashed layers;
- Point fields behind Seat markers and Point handles above them;
- existing tap-to-select and pointer-drag Seat interactions;
- the separate stitch-12 ownership of promoted live controls.

The revised hierarchy was compared against the current Seats sidebar order:
Seats heading/Create Seat, roster, selected detail, Simulation, Venue. Groups is
recommended after selected detail and before the utility sections. Alternatives
for a map-layer drawer, roster/detail interruption, top placement, and Venue
utility placement are compared in the proposal.

## Not validated in this design gate

- No production UI, backend, OSC, state model, simulation, audition or `.pd`
  behaviour changed or was tested.
- The standalone study was checked at a desktop viewport. Real iPad/touch input,
  forced-colours rendering, measured contrast, colour-vision simulation and a
  representative 100-Seat venue remain delivery acceptance checks.
- The study uses representative geometry and state, not a live dashboard.
- Bob has ratified the rail interaction, view-local styles, checklist authoring,
  empty-target behaviour, eye/eye-off icon convention, and subordinate Groups
  placement after Seat detail and before Simulation/Venue.
