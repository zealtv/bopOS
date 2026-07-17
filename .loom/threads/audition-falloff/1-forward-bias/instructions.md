# 1-forward-bias

Implement forward bias in the audition listener geometry.

`python/audition_geometry.py` currently says rear forward-bias is
"deliberately deferred" — this stitch un-defers it.

## Design (pinned)

In `element_terms`, after the distance gain, scale by a forward factor
derived from the angle θ between the listener heading vector and the
direction to the element:

```
forward = REAR_FLOOR + (1 - REAR_FLOOR) * (1 + cos θ) / 2
```

with `REAR_FLOOR = 0.35` as a module constant — directly behind you is
audible but clearly attenuated (~ -9 dB), directly ahead is unity, the
transition is smooth with no seam at ±90°. At distance 0 keep the existing
`(0.0, 1.0)` early return (no direction is defined). Heading 0 is map-up
(−y), positive clockwise — reuse the same convention the balance term
already uses; derive the forward vector consistently and add a unit test
that pins ahead=1.0, behind=REAR_FLOOR, abeam=(1+REAR_FLOOR)/2.

Update the module docstring (drop the "deliberately deferred" sentence).

## Verification

Extend or add unit tests beside the existing geometry tests (find them:
grep test files for `audition_geometry`; the audition thread's tied stitches
in `.loom/tied/preview-*` hold the pattern). Browser-free; run with
`~/.venvs/bopos/bin/python`. Also sanity-run `tools/audition.py`'s import
path (`python -c "import ..."`) to prove nothing else consumed the old
gain shape. `tools/audition.py` consumes `terms_for_positions` — confirm
no caller assumed gain independent of heading.
