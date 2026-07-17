# 1-forward-bias notes

Implemented the pinned forward-bias design in
`python/audition_geometry.py::element_terms`:

- Added module constant `REAR_FLOOR = 0.35`.
- Derived the forward vector consistently with the existing balance/right
  vector convention (heading 0 = map-up `(0, -1)`, positive clockwise):
  `right = (cos heading, sin heading)`, so `forward = (sin heading, -cos
  heading)` (right rotated -90 degrees). Verified algebraically and via the
  new tests that this reproduces the pinned anchors: ahead → cosθ = 1 →
  forward = 1.0; behind → cosθ = -1 → forward = REAR_FLOOR; abeam → cosθ = 0
  → forward = (1 + REAR_FLOOR) / 2.
- `forward` multiplies the existing smooth distance falloff to produce the
  final gain. The distance-0 early return `(0.0, 1.0)` is untouched (no
  direction is defined at zero distance).
- Dropped the "deliberately deferred" sentence from the module docstring.

## tools/audition.py

Read `matrix_for_node` (tools/audition.py:298-309): it calls
`audition_geometry.terms_for_positions(...)` and passes the returned terms
straight through to `audition_matrix.matrix_for_positions(terms)`. It does
not decompose or re-derive gain itself, so it makes no assumption that gain
is independent of heading. No change to `tools/audition.py` was needed or
made — confirmed by import-and-inspect in
`verify_forward_bias.py::audition_caller_sanity`.

## Existing archived test coincidence

`.loom/tied/preview-1-relay-matrix-model/verify_relay_matrix.py` (already
tied, not part of this stitch) has a `geometry_test()` that pins
`element_terms` gain at two points, both of which happen to be directly
"ahead" of the listener in their respective headings (heading 0 with
position `(0, -1)`, and heading 450%360=90 with position `(1, 0)`). Ahead
has forward factor 1.0, so those pinned values (`0.972`) are unaffected by
this change. Not modified, since it's an archived stitch, not a live
regression suite.

## Verification

Ran `~/.venvs/bopos/bin/python verify_forward_bias.py` from this stitch
directory: `ok: 15 checks passed`. Covers the three pinned anchor cases
(ahead/behind/abeam) at two headings, symmetry, the distance-0 early
return, `terms_for_positions` threading the factor through in order, and
the `tools/audition.py` caller sanity check. Browser-free; no Playwright
needed for this stitch (pure Python geometry, no dashboard/server surface).
