# notes — 01-range-field-rendering-fixes

## Verification

```
~/.venvs/bopos/bin/python \
  .loom/tied/26-listener-range-fixes/01-range-field-rendering-fixes/verify_range_field_rendering.py
```

15/15 pass on the fix. Run against pre-fix `main` (changes stashed) the same
script reports **8 failures**, reproducing every defect Bob reported — the guard
is live, not vacuous:

- the out-of-room dashed arc is gone — FAIL (it was there)
- the room clip window coincides with the room rect — FAIL, deltas `[336.4, 269.2]`
- nothing paints right of the room — FAIL
- the wash covers all four quadrants — FAIL, `up-left/up-right/down-left` all read
  bare room, only `down-right` tinted
- the wash is radially symmetric — FAIL, spread 15
- the tick clips with the ring — FAIL
- the field tracks the puck mid-drag — FAIL, field stuck at `translate(5 4)`
  through all six drag samples
- (plus one cascade)

The tied `22-listener-range-ux/02` guard is also green after its two repairs:
32/32 (see `decisions.md`).

Screenshots: `before-*.png` / `after-*.png` (dark, light, and the `-gradient`
pair at range 2.0 which shows the quadrant defect and its repair most clearly).

## Pillow is now a verify dependency

Two checks sample real pixels from a screenshot, because **an SVG element's
`getBoundingClientRect()` reports its geometry box and ignores clipping** — the
DOM literally cannot tell you whether a clipped shape painted outside the room.
That is the whole defect here, so a DOM-only guard would have been vacuous.

`~/.venvs/bopos/bin/pip install Pillow` (done; added to the CLAUDE.md dashboard
test recipe).

Two gotchas worth carrying, both about the *reference* pixel:

- Compare in-room paint against a **bare in-room** pixel, never against a pixel
  outside the room — the room has its own fill, so an outside reference makes
  every in-room probe "differ" and the check passes even when three quadrants
  are unpainted. My first draft had exactly this bug and passed pre-fix.
- Set a *small* range for the gradient probes so there is bare room left to
  sample; do the clipping probes separately at max range.

## Follow-on

`02-retire-listener-toolbar` is unblocked. Note `paintRange()` still writes to
`#listener-readout` / `#listener-range` / `#listener-heading` — those writes go
when the bar goes.
