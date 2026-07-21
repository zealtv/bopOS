# Implementation spec — generator duration field width (stitch 04)

Repo: `/Users/bob/repos/bopOS`. Read first: this stitch's `instructions.md`,
the thread's `../instructions.md`, and `/Users/bob/repos/bopOS/CLAUDE.md`
(house rules + the Playwright gotcha list under "Dashboard browser tests" —
gotcha 10 matters here).

## Diagnosis (orchestrator; confirm in-browser, then fix)

`dashboard/static/js/show.js` renders every generator duration field as
`<span class="show-param-duration"><input type="number" …><select …></span>`
— used by the LFO **period** (around line 735) *and* by each ramp/segment
**duration** (around line 759). Its CSS is:

```
.show-param-duration{display:grid;grid-template-columns:minmax(0,1fr) 70px;gap:5px}
```

The LFO fields sit two-up inside `.show-param-lfo{grid-template-columns:
repeat(2,minmax(0,1fr))}`, inside the 300px inspector sidebar. So the number
input lands at roughly 60px, and the native number spinner takes ~17–20px of
that — Bob's "the number box … is obscured by the increment and decrement
buttons". The 70px unit box is the slack: its options are only `ms`, `s`,
`m`, `h`.

Because both the LFO period and the segment durations share
`.show-param-duration`, one fix covers every generator kind — that is the
"half a fix" the instructions warn about.

## The change

`dashboard/static/css/style.css` only (JS only if genuinely unavoidable — if
so, STOP and report why first).

1. Shrink the unit column: `70px` → a width just sufficient for a two-character
   option plus the native select arrow. Start at **48px**; measure in the
   browser and take the smallest value at which no unit option is clipped in
   either theme, on Chromium. Record the measured value and how you chose it.
2. Add `min-width:0` on the select inside `.show-param-duration` if the grid
   track alone does not shrink it.
3. If 48px of reclaimed width still leaves the number value clipped by the
   spinner at the tightest layout (LFO, 300px sidebar, and again with the
   sidebar collapsed / at the 1020px stacked layout), also trim the number
   input's inline padding within `.show-param-duration` — trim padding before
   you consider touching the spinner itself. Do **not** hide the spinner
   buttons: Bob asked for space to be made, not for the control to be
   removed.
4. Check the mobile override `@media(max-width:760px)` blocks that collapse
   `.show-param-lfo` / `.show-param-segment` to `1fr` still look right.

Prefer existing `--chrome-*` tokens over new one-off values where one fits.

## Constraints

- Do not edit anything under `.loom/tied/` or `.loom/dropped/`, any `.pd`
  file, `facilitator.*`, or loom state. Artifacts go in your stitch dir:
  `.loom/threads/19-show-chrome-fixes/04-lfo-period-field-width.stitching/`.
- The unit `<select>` must remain fully usable and its four options readable.
- No change to the values written to the wire (`durationString()` and the
  `<amount><unit>` grammar are untouched).

## Verifier

Write `verify_generator_field_width.py` in this stitch directory, conventions
copied from `.loom/tied/05-compact-chrome/verify_compact_chrome.py` (repo root
by marker, real `dashboard/server.py` + `tools/simfleet.py` on non-default
ports, headless Chromium, teardown, retained screenshots). Run with
`~/.venvs/bopos/bin/python`.

**Gotcha 10 is binding:** changing the generator `<select>` in-test writes new
args onto the focused message. Build the show fixture with **one message per
generator kind** (LFO, ramp/segments, and any other kind with a numeric
duration arg) and select each message rather than switching kinds.

Assert at least:

1. For every generator kind's duration/period number input: the input's
   content box width minus the spinner's width leaves room for the rendered
   value — e.g. set a realistic multi-character value (`1250`), then compare
   the input's client width against the value's measured text width plus the
   spinner width, and assert the value is not clipped. Gather all
   measurements in a single `page.evaluate` (gotcha 9).
2. Same at the inspector's normal width **and** with the sidebar collapsed
   (or the narrow/stacked layout), and at 768px.
3. The unit select still shows its selected option untruncated for the widest
   option (`ms`), and still contains all four options.
4. Changing period amount + unit still round-trips into the message's wire
   preview / stored arg unchanged (the `<amount><unit>` string).
5. Retained screenshots of the LFO and the segment/ramp inspector, light and
   dark.

Then re-run these tied suites **unmodified** and report their output:

```
.loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
.loom/tied/04-named-section-dividers/verify_named_dividers.py
.loom/tied/05-compact-chrome/verify_compact_chrome.py
.loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
.loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
.loom/tied/01-inspector-toggle-overlap/verify_inspector_toggle_overlap.py
.loom/tied/02-step-and-divider-icons/verify_step_divider_icons.py
.loom/tied/03-divider-rule-styling/verify_divider_rules.py
```

plus the automation suites if any assert these field widths (check
`.loom/tied/automation-*/`). Re-running regenerates their retained
screenshots — afterwards run `git checkout -- .loom/tied/`. Delete any
`__pycache__/` your runs create inside stitch directories.

Playwright house rules that bit previous sessions: elements in a non-active
tab panel need `state="attached"` not visible; `#ws-status` is an empty span
when online (also `state="attached"`); no `scroll_into_view_if_needed` or
actionability waits on Show rows or automation markers (heartbeat re-renders
+ CSS animations make them perpetually unstable) — use a one-shot
`page.evaluate` `scrollIntoView` then a fresh `bounding_box()`; compare rects
gathered from ONE scroll state; one type-aware `page.on("dialog")` handler;
`page.wait_for_function(expr, arg=value)`; `inner_text` applies CSS
`text-transform`; a fixture manifest's string param must omit `default` (the
validator only allows numeric min/max/default).

## Deliverables

- the edited `style.css`
- `verify_generator_field_width.py`
- `verification.md` — exact commands run, real output tails, the measured
  unit-box width and how it was chosen, any deviation with reasoning
- retained screenshots

## Acceptance checks (run them; paste real output)

Run the new verifier and each tied suite listed above; every one must end
`0 failure(s)`. If a tied suite asserts something this change legitimately
alters, STOP and report the exact assertion — do not edit a tied suite. Do
not commit; leave the tree for the orchestrator.
