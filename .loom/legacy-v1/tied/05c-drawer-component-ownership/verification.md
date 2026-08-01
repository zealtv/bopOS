# Verification

Passed on 2026-07-30:

```text
./tools/run-tests.sh fast
Ran 250 tests — OK

./tools/run-tests.sh browser
19/19 browser verifiers passed
  (including verify_generator_drawer.py and verify_show_generator_drawer.py,
   which exercise the drawer in two different hosts)

python cascade_probe.py <old css> > before.json
python cascade_probe.py <new css> > after.json
python cascade_probe.py --diff before.json after.json
no rendered change in any real host
```

`cascade-result.txt` is the diff output. The behavioral suites are necessary but
not sufficient here — a rule that stops applying leaves the DOM identical, so
they cannot see a cascade slip. `cascade_probe.py` closes that gap: 27 computed
properties on every element of the drawer, in each of the three real hosts, for
each of the three generator kinds.

| context | elements | differing |
|---|---|---|
| `live-card` × lfo/fade/loop | 49 / 39 / 46 | **0 / 0 / 0** |
| `device-control` × lfo/fade/loop | 49 / 39 / 46 | **0 / 0 / 0** |
| `show-inspector-section` × lfo/fade/loop | 49 / 39 / 46 | **0 / 0 / 0** |
| bare `<div>` × lfo/fade/loop | 49 / 39 / 46 | 46 / 36 / 43 |

Zero rendered change in every host the drawer is mounted in today, which is the
claim this stitch needed to make. The bare-`<div>` column is the point of the
change rather than a regression: it is the mount point `06` and `08` will
create, and under the old selectors none of the 68 rules reached it. The drawer
goes from unstyled sprawl (1280 × 673, `display:block`) to the correct compact
drawer (320 × 177, grid).

The probe is kept in the stitch and locates the repo by marker
(`tools/simfleet.py`), not by `..` hops, so it still runs from `tied/`.

## Not verified

No screenshots were taken. The computed-style diff is a stronger claim than a
pixel comparison for a cascade question and made a screenshot pass redundant;
the `shoot.py` route also still carries the `bopos.theme` / `bopos-theme` key
bug that stitch `03` found.

Firefox is unverified — the probe is Chromium-only, and two of the re-anchored
rules are `::-moz-range-*` pseudo-elements whose cascade cannot be checked in
Chromium at all. Their specificity transformation is identical to the rules that
were verified, so the risk is low but not measured.

No physical device, iPad/touch, Pure Data, audible or hardware verification was
performed. This stitch changes CSS selectors only — no declaration, markup, or
JS changed.
