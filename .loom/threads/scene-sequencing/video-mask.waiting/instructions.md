# video-mask

**Idea (unresolved home — decide before building):** use video as a mask across the 2D
installation space. Sample a channel (e.g. luminance) of a video at each device's
(x, y) position; map that value to a parameter on the device's patch. Visual gradients
and video textures then create sweeps and effects across the space. Review §10.

Notes:
- Generalises `spatial-audio`'s moving point: point+radius+falloff is just one
  procedurally-generated mask; video is an arbitrary authored one. Consider designing
  the spatial-audio Stage A internals as "mask → per-device value → parameter" from the
  start so video slots in later.
- Open question: dashboard layer (canvas/video decode in the backend or browser,
  sampled at device positions, sent as parameter values), a separate application
  feeding the dashboard OSC, or something else entirely.
- Rate/bandwidth: per-device parameter updates at ~20–30 Hz is the same budget as
  spatial-audio Stage A; same Stage-B broadcast trick doesn't apply (video isn't
  compactly describable), so this may cap fleet size unless masks are pre-rendered to
  per-device automation curves (which the scene language could then play back — worth
  considering as the v1: offline video → baked automation).

Do not start until `spatial-audio` Stage A works and the scene language exists in some
form; then decide the home.

---
**2026-07-08 (Bob):** if the scene language grows node-side spatial primitives
(compact gradient/noise messages expanded on the node — see
`../scene-language-spec/bob-design-notes-2026-07-08.md`), that *mostly
dissolves* this approach. Keep only if it turns out to be an easy win — video
as a mask would still be an extremely ergonomic authoring workflow.
