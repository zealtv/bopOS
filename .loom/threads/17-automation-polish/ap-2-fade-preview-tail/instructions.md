# ap-2-fade-preview-tail — single-segment fade preview grows a false tail

**Bug (Bob, 2026-07-20):** the fade preview in the Show inspector draws a
release-like segment at the end of a **one-segment** fade. Screenshot:
`.loom/threads/dashboard-theme-toggle/Screenshot 2026-07-20 at 09.49.29.png`
— wire form `/p/gain [f:0, f:1, s:5s] -> g1` (from 0, to 1, over 5s)
renders as a rising line that then drops sharply back down at the right
edge. A single segment must be a straight line from end to end of its
representation; the preview must trace exactly the authored envelope.

## Do

- Find the preview renderer (static SVG generator preview from
  `automation-5-waveform-marker`, in `dashboard/static/js/show.js` /
  `paramspec.js`). Diagnose why a trailing point is emitted — likely the
  path closes back toward a baseline/current value, or a phantom final
  segment is appended when `from` is present.
- Fix so the polyline is exactly the segment chain: N segments → N+1
  points, no baseline return. Check multi-segment fades and the
  `from`-omitted case too (preview starting at current/unknown value —
  whatever the tied behaviour intends), and make sure the same geometry
  helper used by any value-axis marker rendering isn't shared-and-broken
  in the live view.
- While in there, sanity-check the small `f · 0 to 1` narrow-preview
  variant in `Screenshot 2026-07-20 at 09.48.11.png` (0→0 fade renders
  flat — correct — but confirm the same tail bug doesn't distort it).

## Verify

Playwright or pure-JS unit check (house pattern): author a one-segment
fade 0→1 over 5s, read the preview SVG path/polyline points, assert they
are exactly two points (monotonic straight line) and the last point's y
corresponds to the destination value. Add a two-segment case asserting
three points. Screenshot for the stitch.
