# 09-patches-deploy-row — verification

## Measured, before and after

`probe_target_object.py` (kept here), against the real running app at 1280:

| | before | after |
| --- | --- | --- |
| `.fleet-patch-deploy` height | **74px** | **37px** |
| `#patch-select` | 984 × 37 | 260 × 37 |
| `#patch-target` | 984 × 37 | 260 × 37 |
| `.fleet-patch-actions` | 230 × 24 | 230 × 24 |
| rows occupied | 2 | **1** |

`deploy-row-desktop.png` and `deploy-row-narrow.png` show the
result at 1280 and at 700 (below the existing 760px breakpoint, where the three
still stack full-width as they always did).

## The object comparison

| candidate | height at rest |
| --- | --- |
| `<select>` | 37px |
| device-domain `TargetPicker`, closed | 51px |

Reasoning in `decisions.md`. The picker measurement is taken from the Assets
tab, its only existing device consumer, rather than from a hypothetical mount.

## The sweep

Every container in `#tab-patches` whose own height exceeds its tallest control.
After the change only `#fleet-patch-panel` and `#manifest-editor` remain, and
both are panels that are supposed to be multi-row. `.fleet-patch-deploy` and
`.editor-launch` no longer appear.

## Guard, verified in both directions

Two assertions in `tests/verify_device_patch_targeting.py`.

Green on the fixed tree. On the pre-change tree (`git stash push` of
`style.css` + `index.html`):

```
[FAIL] the deploy row is a single line -- {'height': 74, 'tallest': 37, 'centreSpread': 43}
[FAIL] patch, target and actions share one vertical centre -- {'height': 74, 'tallest': 37, 'centreSpread': 43}
```

## Suites

* `fast` — **268** tests, OK (unchanged; this stitch adds no browser-free test).
* `tools/run-tests.sh browser` — **23/23 green**, one clean run.
* `verify_device_patch_targeting.py` standalone — passes, including the deploy
  and pin flows either side of the new assertions, so the relabelling
  `#patch-target` drives is intact.

## Not covered

No hardware. This is markup and CSS in the dashboard document.

The Remote view does not carry this panel, so `facilitator.css` is untouched and
there is no coarse-pointer question here — unlike the component collapses in
this thread, nothing was measured for `49-remote-ipad-restyle`.

The range just above the breakpoint — where three capped columns plus the
buttons first get tight — was measured rather than reasoned about:

| viewport | deploy row | `#patch-target` |
| --- | --- | --- |
| 1280px | 37px | 260px |
| 900px | 37px | 260px |
| 800px | 37px | 246px |
| 780px | 37px | 236px |

One line holds all the way down to the 760px breakpoint, the selects giving
gracefully from their 260px cap toward the `minmax(140px, …)` floor. Shot at
800px as well (`deploy-row-tight.png`).
