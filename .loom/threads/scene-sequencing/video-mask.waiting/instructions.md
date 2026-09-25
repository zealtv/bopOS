# video-mask

**Status:** waiting — idea with no home yet; after the scene language exists
**Goal:** use video as a mask over the installation — sample a channel (e.g.
luminance) at each device's position and map it to a patch parameter, so visual
gradients become sweeps across the space. Context: review §10.

## Notes

- Generalises spatial points: point + radius + falloff is one procedural mask;
  video is an authored one.
- **Where it runs** is open: dashboard (decode in backend or browser, sample at
  device positions), a separate app sending OSC, or other.
- **Bandwidth:** per-device updates at 20–30 Hz may cap fleet size. A likely v1:
  bake video offline into per-device automation curves, played by the scene
  language.
- **Bob (2026-07-08):** if the language gets node-side spatial primitives
  (compact gradient/noise messages expanded on the node), that *mostly
  dissolves* this. Keep only if it's an easy win — video masks would still be
  very ergonomic to author.
