# Verification — generator duration field width (thread 19, stitch 04)

## Diagnosis, confirmed in-browser

The spec's diagnosis was right about the symptom and about the shared
`.show-param-duration` grid, but the dominant cause turned out to be a dead
cascade rule, measured live in Chromium:

Before the change, at 1280px with the inspector at its normal 300px width, the
LFO period input measured:

```
[FAIL] 1280/lfo: lfo period value '1250' not clipped by the spinner
       -- client=45.0 scroll=59.0 pad=16.0 text=27.8 spinner=15.2
```

45px of padding box against 59px of required content (16px padding + 27.8px of
`1250` + 15.2px of inner spin button) — exactly Bob's "the number box is
obscured by the increment and decrement buttons".

Why only 45px? `8884c69` ("The fade segment row learns how narrow the inspector
really is") introduced

```css
@container show-inspector (max-width:380px){
  .show-param-segment{grid-template-columns:1fr}
  .show-param-segment button{width:100%}
  .show-param-lfo{grid-template-columns:1fr}}
```

and its commit message says "at container widths at or below 380px the segment
row **and LFO grid** stack to one column". But it inserted the block *before*
the base `.show-param-lfo{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}`
declaration. Same specificity, later rule wins — so the segment half took
effect and the LFO half never did. Inside the 300px sidebar the LFO grid stayed
two-up, giving each column ~100px and the period number input 45px.

That is why shrinking the unit box alone could not fix it: the deficit at the
LFO period was 14px, and the entire reclaimable slack in the unit column is
also ~14px (see below).

## The change (`dashboard/static/css/style.css`, CSS only)

1. `.show-param-duration` unit track `70px` → **`56px`**, plus
   `.show-param-duration select{min-width:0}` so the narrower track actually
   shrinks the select. This is Bob's suggested remedy and it benefits every
   generator kind's duration field, wide container or narrow.
2. The `@container show-inspector (max-width:380px)` block moved to *after* the
   base `.show-param-lfo` rule, so the LFO half of that already-ratified
   container query finally applies. No declarations were added, removed or
   changed inside it — only its position in the file.

Nothing else changed: no JS, no spinner hiding, no padding trimming (unneeded
once the LFO grid stacks), no change to `durationString()` or the
`<amount><unit>` wire grammar.

### How 56px was chosen

Measured, not guessed. The spec said start at 48px and take the smallest value
at which no unit option is clipped. Measurement in Chromium at the app's real
inspector font/padding:

- the four-option `ms/s/m/h` select's own **min-content width is 55.0px** (an
  off-DOM clone of the live select sized `width:min-content`);
- at the spec's suggested 48px the select renders 46px of padding box — below
  its min-content, i.e. the widest option `ms` gets squeezed. The verifier
  caught this: `[FAIL] ... unit select not truncated -- rect=48.0 client=46.0
  intrinsic=55.0`;
- **56px** is the smallest 4px-grid value at or above 55px. Live measurement at
  56px: `rect=56.0 client=54.0 scroll=54.0 intrinsic=55.0`, no truncation, in
  both themes and at both widths.

So the reclaim from the unit box is 14px (70 → 56), and the number input keeps
comfortable margins everywhere:

| context | period/duration input padding box | needed (pad+text+spinner) |
|---|---|---|
| 1280px, 300px sidebar, LFO period | 144px | 58.8px |
| 1280px, 300px sidebar, fade/loop segment duration | 126px | 58.8px |
| 768px stacked, LFO period | 255px | 57.8px |
| 768px stacked, loop segment durations | 209px | 58.8px |

Screenshots retained: `lfo-fields-1280-dark.png`, `lfo-fields-1280-light.png`,
`segments-1280-dark.png`, `segments-1280-light.png` (element crops of the
generator field blocks, both themes).

### Deviations from the spec, and why

- **56px rather than 48px.** 48px truncates the `ms` option — measured, see
  above. The spec's own rule ("smallest value at which no unit option is
  clipped") selects 56px once the select's real min-content width is measured.
- **A second CSS change (the container-block move).** The spec allowed only the
  unit-column shrink and warned to stop and report before touching JS. This is
  still CSS-only and adds no new declarations, but it is a second edit, so:
  without it, shrinking the unit box to 56px leaves the LFO period input at
  59px against 58.8px of required content — a 0.2px margin, i.e. still visually
  broken the moment the value is five digits or the font is a hair wider. It is
  also a plain cascade bug in tied work whose author's stated intent
  (commit message of `8884c69`) is exactly what the move restores. The
  instructions' outcome ("the LFO period value is fully legible ... at the
  inspector's normal width") is not reachable by the unit box alone.
- **"Sidebar collapsed" is asserted as *collapse hides the form, re-open keeps
  it legible".** Collapsing the inspector replaces it with a 40px rail, so
  there is no narrower state in which a duration field is visible; the narrow
  case that does exist is the 768px stacked layout, which is also verified.

## Commands run and real output tails

All from `/Users/bob/repos/bopOS` with `~/.venvs/bopos/bin/python`.

### New verifier

```
$ ~/.venvs/bopos/bin/python .loom/threads/19-show-chrome-fixes/04-lfo-period-field-width.stitching/verify_generator_field_width.py
[PASS] unit column track is 56px -- {'cols': '146px 56px', 'gap': '5px', 'selMinWidth': '0px'}
[PASS] unit select carries min-width:0 -- {'cols': '146px 56px', 'gap': '5px', 'selMinWidth': '0px'}
[PASS] LFO grid stacks to one column inside the 300px inspector -- '207px'
[PASS] inspector sidebar is at its normal 300px width -- 300
[PASS] 1280/lfo: lfo period value '1250' not clipped by the spinner -- client=144.0 scroll=144.0 pad=16.0 text=27.8 spinner=15.0
...
[PASS] wire preview keeps the <amount><unit> period string -- '/p/gain [s:lfo, s:sine, f:0, f:1, s:1250ms] -> all'
[PASS] changing the unit round-trips into the wire preview -- '/p/gain [s:lfo, s:sine, f:0, f:1, s:1250s] -> all'
[PASS] persisted LFO arg keeps the <amount><unit> grammar -- ['lfo', 'sine', 0.0, 1.0, '1250s']
...
[PASS] no page-level horizontal overflow at 768px
[PASS] browser emitted no page errors -- []

--- measurements ---
1280px, sidebar open, lfo              lfo period           input rect=146.0 client=144.0 scroll=144.0 pad=16.0 text=27.8 spinner=15.0 | select rect=56.0 intrinsic=55.0
1280px, sidebar open, fade             segment duration #0  input rect=128.0 client=126.0 scroll=126.0 pad=16.0 text=27.8 spinner=15.0 | select rect=56.0 intrinsic=55.0
1280px, sidebar open, loop             segment duration #0  input rect=128.0 client=126.0 scroll=126.0 pad=16.0 text=27.8 spinner=15.0 | select rect=56.0 intrinsic=55.0
1280px, sidebar open, loop             segment duration #1  input rect=128.0 client=126.0 scroll=126.0 pad=16.0 text=27.8 spinner=15.0 | select rect=56.0 intrinsic=55.0
1280px, light theme, loop              segment duration #0  input rect=128.0 client=126.0 scroll=126.0 pad=16.0 text=27.8 spinner=15.0 | select rect=56.0 intrinsic=55.0
1280px, light theme, loop              segment duration #1  input rect=128.0 client=126.0 scroll=126.0 pad=16.0 text=27.8 spinner=15.0 | select rect=56.0 intrinsic=55.0
1280px, light theme, lfo               lfo period           input rect=146.0 client=144.0 scroll=144.0 pad=16.0 text=27.8 spinner=15.0 | select rect=56.0 intrinsic=55.0
1280px, re-opened sidebar, lfo         lfo period           input rect=146.0 client=144.0 scroll=144.0 pad=16.0 text=27.8 spinner=15.0 | select rect=56.0 intrinsic=55.0
1280px, after edit, lfo                lfo period           input rect=146.0 client=144.0 scroll=144.0 pad=16.0 text=27.8 spinner=15.0 | select rect=56.0 intrinsic=55.0
768px, lfo                             lfo period           input rect=256.5 client=255.0 scroll=255.0 pad=16.0 text=27.8 spinner=14.0 | select rect=56.0 intrinsic=55.0
768px, loop                            segment duration #0  input rect=210.7 client=209.0 scroll=209.0 pad=16.0 text=27.8 spinner=15.0 | select rect=56.0 intrinsic=55.0
768px, loop                            segment duration #1  input rect=210.7 client=209.0 scroll=209.0 pad=16.0 text=27.8 spinner=15.0 | select rect=56.0 intrinsic=55.0

0 failure(s)
```

67 PASS lines, 0 failures.

### Tied suites, re-run unmodified

```
=== .loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
0 failure(s)
=== .loom/tied/04-named-section-dividers/verify_named_dividers.py
0 failure(s)
=== .loom/tied/05-compact-chrome/verify_compact_chrome.py
0 failure(s)
=== .loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
0 failure(s)
=== .loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
0 failure(s)
=== .loom/tied/01-inspector-toggle-overlap/verify_inspector_toggle_overlap.py
0 failure(s)
=== .loom/tied/02-step-and-divider-icons/verify_step_divider_icons.py
0 failure(s)
=== .loom/tied/03-divider-rule-styling/verify_divider_rules.py
0 failure(s)
```

Automation suites that touch these selectors (`grep -l` over
`.loom/tied/*/verify_*.py` for `show-param-duration|show-param-lfo|param-lfo|
param-segment`) plus the take-over suite:

```
=== .loom/tied/ap-1-fade-inspector-layout/verify_fade_inspector_layout.py
[PASS] narrow: lfo period input has usable width
[PASS] wide: destination and duration share a row
[PASS] browser emitted no console errors
All fade inspector layout checks passed.

=== .loom/tied/automation-2-show-builder-gui/verify_show_param_builder.py
[PASS] one-row loop refuses to update args
[PASS] browser emitted no console errors
All Show param builder checks passed.

=== .loom/tied/automation-3-animated-takeover/verify_automation_takeover.py
[PASS] take-over clears the glyph
[PASS] browser emitted no console errors
All automation take-over checks passed.
```

(`ap-1` and the `automation-*` suites print "All ... checks passed" instead of
an "N failure(s)" line.)

`automation-2` failed once on its first run with
`RuntimeError: dashboard exited before serving HTTP` — a loopback port
collision in its own `free_port` helper, not an assertion. It passes on re-run.

### One pre-existing failure, not caused by this change

```
=== .loom/tied/automation-5-waveform-marker/verify_waveform_marker.py
playwright._impl._errors.TimeoutError: Page.wait_for_selector: Timeout 30000ms exceeded.
Call log:
  - waiting for locator(".seat-card[data-live-id=\"0\"] label[data-param-path=\"fade\"] [data-auto-fade-progress]") to be visible
```

Reproduced identically with this stitch's CSS change stashed
(`git stash push dashboard/static/css/style.css` → same timeout → `git stash
pop`), so it is pre-existing on `main` at `2d69554` and unrelated: it waits on
a **Dashboard**-tab seat card automation marker, nothing in
`.show-param-duration` / `.show-param-lfo`.

### Housekeeping

Tied screenshots regenerated by the re-runs were reverted with
`git checkout -- .loom/tied/`; `find .loom -name __pycache__ -type d` removed.
`git status --short` afterwards shows only `dashboard/static/css/style.css`
modified plus this untracked stitch directory (and the pre-existing untracked
`dashboard/shows/`). Nothing committed.
