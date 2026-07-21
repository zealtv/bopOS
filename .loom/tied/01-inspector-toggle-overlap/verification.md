# Verification — inspector collapse toggle vs edit-bar delete (19/01)

## Confirmed root cause

The spec's diagnosis is **confirmed in the browser**, exactly as written.

`.show-inspector-toggle` is a child of `.show-inspector-panel` (see
`dashboard/static/js/show.js:487-490`). In the wide layout the panel is
`position:sticky`, so it is the toggle's containing block and the toggle lands
on the panel's top-right. Inside `@media(max-width:1020px)` the panel was
`position:static` (and the shell too), so the toggle's containing block fell
through to `.show-workspace` (`position:relative`) and the toggle rendered at
the **top-right of the whole workspace**, directly over the edit bar's delete
button.

Measured pre-fix at 900px (single `page.evaluate`, one scroll state):

```
toggle (incl. ::after inset:-8px): x=826 y=270 w=44 h=44   (raw 834,278,28,28)
delete button (incl. ::after):     x=819 y=269 w=52 h=52   (raw 825,275,40,40)
inspector panel:                   x=48  y=852 w=803 h=817
```

The toggle sat ~580px above its own panel — squarely on the delete button.
(Note: `.show-inspector-shell` carries `container-type:inline-size`, which one
might expect to establish a containing block; empirically in Chromium it did
not rescue this case — the measured containing block was the workspace.)

## Fix

One rule, CSS only, in `dashboard/static/css/style.css`, inside
`@media(max-width:1020px)`:

```
- .show-inspector-panel{position:static;max-height:none;margin-top:var(--chrome-gap)}
+ .show-inspector-panel{position:relative;top:auto;max-height:none;margin-top:var(--chrome-gap)}
```

`position:relative` restores the panel as the toggle's containing block in the
narrow layout; `top:auto` neutralises the base rule's sticky `top:72px` offset
(a relatively-positioned box would otherwise be shifted 72px down). No z-index,
no new offsets, no JS change, no new one-off values (the rule reuses the
existing `--chrome-gap`). Wide layout is untouched — the panel is still
`position:sticky;top:72px` there, and the `padding-right:34px` heading
reservation is unchanged (asserted).

## Commands run and real output

### New suite (post-fix)

```sh
cd /Users/bob/repos/bopOS
~/.venvs/bopos/bin/python .loom/threads/19-show-chrome-fixes/01-inspector-toggle-overlap.stitching/verify_inspector_toggle_overlap.py
```

```
[PASS] 900px short inspector (divider): collapse toggle exists
[PASS] 900px short inspector (divider): delete button exists
[PASS] 900px short inspector (divider): toggle hit area does not intersect delete button
[PASS] 900px tall inspector (LFO message): collapse toggle exists
[PASS] 900px tall inspector (LFO message): delete button exists
[PASS] 900px tall inspector (LFO message): toggle hit area does not intersect delete button
[PASS] 900px: LFO inspector is taller than the divider inspector
[PASS] 900px: toggle sits inside the inspector panel
[PASS] 768px short inspector (divider): collapse toggle exists
[PASS] 768px short inspector (divider): delete button exists
[PASS] 768px short inspector (divider): toggle hit area does not intersect delete button
[PASS] 768px tall inspector (LFO message): collapse toggle exists
[PASS] 768px tall inspector (LFO message): delete button exists
[PASS] 768px tall inspector (LFO message): toggle hit area does not intersect delete button
[PASS] 768px: LFO inspector is taller than the divider inspector
[PASS] 768px: toggle sits inside the inspector panel
[PASS] 1280px short inspector (divider): collapse toggle exists
[PASS] 1280px short inspector (divider): delete button exists
[PASS] 1280px short inspector (divider): toggle hit area does not intersect delete button
[PASS] 1280px: toggle is contained by the inspector panel
[PASS] 1280px tall inspector (LFO message): collapse toggle exists
[PASS] 1280px tall inspector (LFO message): delete button exists
[PASS] 1280px tall inspector (LFO message): toggle hit area does not intersect delete button
[PASS] 1280px: toggle stays pinned to the panel's top-right
[PASS] 1280px: inspector heading keeps its 34px toggle reservation
[PASS] browser emitted no page errors

0 failure(s)
```

The same suite run **before** the CSS change reported `6 failure(s)` — the two
narrow widths x (short, tall) overlap assertions plus the two narrow
toggle-inside-panel assertions. That is the negative control: the suite
genuinely detects the defect.

### Tied regression suites (re-run unmodified)

```sh
for f in .loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py \
         .loom/tied/04-named-section-dividers/verify_named_dividers.py \
         .loom/tied/05-compact-chrome/verify_compact_chrome.py \
         .loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py \
         .loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py; do
  echo "===== $f"; ~/.venvs/bopos/bin/python "$f" 2>&1 | grep -E "^\[FAIL\]|failure\(s\)"
done
```

```
===== .loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
0 failure(s)
===== .loom/tied/04-named-section-dividers/verify_named_dividers.py
0 failure(s)
===== .loom/tied/05-compact-chrome/verify_compact_chrome.py
0 failure(s)
===== .loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
0 failure(s)
===== .loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
0 failure(s)
```

Afterwards `git checkout -- .loom/tied/` restored the regenerated tied
screenshots, and the `__pycache__/` directories the runs created inside
`.loom/tied/02-inspector-sidebar/` and
`.loom/tied/p1-zero-value-and-transport-bugs/` were deleted.

## Retained artifacts

- `narrow-900-dark.png`, `narrow-900-light.png` — 900px viewport, inspector
  expanded on the LFO message (tall content). The `›` collapse toggle is on the
  inspector panel's top-right beside the "wobble" heading; the edit bar's `✕`
  delete button is far above it, unobstructed.

## Deviations from the spec

None. CSS-only fix as anticipated; no `show.js` change was needed.
