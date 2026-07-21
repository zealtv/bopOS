# Implementation spec — step/divider glyphs (stitch 02)

Repo: `/Users/bob/repos/bopOS`. Read first: this stitch's `instructions.md`
and `decisions.md` (the ruled design — implement those glyphs, do not
redesign), the thread's `../instructions.md`, and
`/Users/bob/repos/bopOS/CLAUDE.md` (house rules + the Playwright gotcha list
under "Dashboard browser tests").

## The change

In `dashboard/static/js/show.js`, `editBarButton()` (around line 464) takes a
raw-HTML `glyph`. The two calls to fix are `add-step` (`"+"`) and
`add-divider` (`"—"`), around lines 472–473. Replace both glyphs with the
inline SVG described in `decisions.md`. Keep `escapeHtml` applied to the
labels and accessible names exactly as now; the glyph is already injected
raw, so an SVG string works — do not start escaping it.

In `dashboard/static/css/style.css`, widen `.show-edit-bar-glyph` from
`width:14px` to `20px` and add whatever minimal rule the SVG needs
(`.show-edit-bar-glyph svg{display:block;flex:none}` or similar). Do not
alter the button's size, padding, `::after` touch expansion, or the
`.show-edit-bar-label{display:none}` narrow behaviour.

Check the widened glyph does not push the edit bar into overflow at 768px —
if it does, prefer trimming the glyph gap over shrinking the icon, and say so
in `verification.md`.

## Constraints

- Only `dashboard/static/js/show.js` and `dashboard/static/css/style.css`.
- Do not edit anything under `.loom/tied/` or `.loom/dropped/`, any `.pd`
  file, `facilitator.*`, or loom state. Artifacts go in your stitch dir:
  `.loom/threads/19-show-chrome-fixes/02-step-and-divider-icons.stitching/`.
- No icon font, no external asset, no build step — the app is self-contained.
- Accessible names stay `Add step` / `Add divider`; glyph span stays
  `aria-hidden="true"`.
- Icons must work in both themes (they inherit `currentColor`) and in the
  disabled state (the button's `opacity:.4` handles it — check it reads).

## Verifier

Write `verify_step_divider_icons.py` in this stitch directory, conventions
copied from `.loom/tied/05-compact-chrome/verify_compact_chrome.py` (repo
root by marker, real `dashboard/server.py` + `tools/simfleet.py` on
non-default ports, headless Chromium, teardown, retained screenshots). Run it
with `~/.venvs/bopos/bin/python`. Assert at least:

1. Both buttons still resolve by accessible name (`Add step`, `Add divider`)
   at 1280px and 768px.
2. Clicking `Add step` adds a step row and clicking `Add divider` adds a
   divider row — the right item kind each time (read back the rows).
3. Each button's glyph span contains an `svg` element and both SVGs are
   non-empty and distinct from each other.
4. At 768px (labels hidden) both buttons are visible, non-overlapping with
   their neighbours, and the edit bar produces no horizontal page overflow.
5. Retained screenshots of the edit bar at 1280px and 768px, light and dark,
   so Bob can eyeball the glyphs.

Then re-run these tied suites **unmodified** and report their output:

```
.loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
.loom/tied/04-named-section-dividers/verify_named_dividers.py
.loom/tied/05-compact-chrome/verify_compact_chrome.py
.loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
.loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
.loom/tied/01-inspector-toggle-overlap/verify_inspector_toggle_overlap.py
```

Re-running them regenerates their retained screenshots — afterwards run
`git checkout -- .loom/tied/` to restore those artifacts. Delete any
`__pycache__/` your runs create inside stitch directories.

Playwright house rules that bit previous sessions: elements in a non-active
tab panel need `state="attached"` not visible; `#ws-status` is an empty span
when online (also `state="attached"`); no `scroll_into_view_if_needed` or
actionability waits on Show rows (heartbeat re-renders + CSS animations make
them perpetually unstable) — use a one-shot `page.evaluate` `scrollIntoView`
then a fresh `bounding_box()`; compare rects gathered from ONE scroll state;
one type-aware `page.on("dialog")` handler; `page.wait_for_function(expr,
arg=value)`; `inner_text` applies CSS `text-transform`.

## Deliverables

- the two edited source files
- `verify_step_divider_icons.py`
- `verification.md` — exact commands run, real output tails, any deviation
  from the spec/decisions with reasoning
- retained screenshots

## Acceptance checks (run them; paste real output)

```sh
cd /Users/bob/repos/bopOS
~/.venvs/bopos/bin/python .loom/threads/19-show-chrome-fixes/02-step-and-divider-icons.stitching/verify_step_divider_icons.py
~/.venvs/bopos/bin/python .loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
~/.venvs/bopos/bin/python .loom/tied/04-named-section-dividers/verify_named_dividers.py
~/.venvs/bopos/bin/python .loom/tied/05-compact-chrome/verify_compact_chrome.py
~/.venvs/bopos/bin/python .loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
~/.venvs/bopos/bin/python .loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
~/.venvs/bopos/bin/python .loom/tied/01-inspector-toggle-overlap/verify_inspector_toggle_overlap.py
git checkout -- .loom/tied/
```

Every suite must end `0 failure(s)`. If a tied suite asserts something this
change legitimately breaks (e.g. it matches on the literal `+` glyph text),
STOP and report the exact assertion — do not edit a tied suite. Do not commit;
leave the tree for the orchestrator.
