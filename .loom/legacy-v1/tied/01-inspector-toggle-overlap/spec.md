# Implementation spec — inspector collapse toggle vs edit-bar delete (stitch 01)

Repo: `/Users/bob/repos/bopOS`. Read first: this stitch's `instructions.md`,
the thread's `../instructions.md`, and `/Users/bob/repos/bopOS/CLAUDE.md`
(house rules + the Playwright gotcha list under "Dashboard browser tests").

## Diagnosis (already done by the orchestrator — confirm, then fix)

In `dashboard/static/css/style.css`:

- Wide layout: `.show-workspace{position:relative}`,
  `.show-inspector-shell{position:absolute;…}`,
  `.show-inspector-panel{position:sticky;…}`,
  `.show-inspector-toggle{position:absolute;top:10px;right:10px}` — the toggle
  is contained by the *sticky panel*, so it sits in the panel's top-right.
  Correct.
- Inside `@media(max-width:1020px)` the shell and the panel both become
  `position:static`. The toggle's containing block therefore falls through to
  `.show-workspace` (the nearest positioned ancestor), so it renders at the
  **top-right of the whole workspace** — on top of the edit bar, where the
  delete button lives. That is the defect Bob saw.

The fix is expected to be a containing-block fix (give the panel a position
context in the narrow block, e.g. `position:relative`), not z-index and not a
new offset. Verify the diagnosis in the browser before committing to it; if
the real cause differs, follow the evidence and say so in `verification.md`.

## Constraints

- Work only in `dashboard/static/css/style.css` (and `show.js` **only** if CSS
  genuinely cannot do it — if so, stop and report before making the JS change).
- Do not edit anything under `.loom/tied/` or `.loom/dropped/`, any `.pd`
  file, `facilitator.*`, or loom state. Your stitch directory
  (`.loom/threads/19-show-chrome-fixes/01-inspector-toggle-overlap.stitching/`)
  is where all artifacts go.
- The Show tab's chrome runs on the `--chrome-*` variables in `:root`; prefer
  those over new one-off values.
- Wide-viewport layout must be unchanged (the toggle stays pinned to the
  panel's top-right, `padding-right:34px` reservation on the panel's first
  heading still applies).
- The toggle keeps its accessible name and its `::after{inset:-8px}` touch
  expansion; the expanded hit area must also not intersect the delete button.

## Outcome to hit

At narrow widths, with the inspector expanded, the collapse toggle's box
(including its `::after` expansion) does not intersect the edit bar's delete
button's box, for a short inspector (divider selected) and a tall one
(message with an LFO generator). Wide layout unchanged.

## Verifier

Write `verify_inspector_toggle_overlap.py` in this stitch directory. Copy the
conventions from `.loom/tied/05-compact-chrome/verify_compact_chrome.py`
(newest tied suite): locate the repo root by marker (`tools/simfleet.py`),
launch the real `dashboard/server.py` + `tools/simfleet.py` on non-default
ports, headless Chromium via Playwright, teardown, retained screenshots.
Run it with `~/.venvs/bopos/bin/python`.

Assertions, at minimum:

1. Narrow viewport (pick one clearly inside `max-width:1020px`, e.g. 900px
   wide) with inspector expanded: toggle rect and delete-button rect do not
   intersect — **gather both rects in a single `page.evaluate`** (gotcha 9),
   and include the `::after` inset expansion in the toggle's effective rect.
2. Same at a very narrow width (768px).
3. Same for both a short inspector (divider row selected) and a tall one
   (a message step with an LFO generator).
4. Wide viewport (1280px): toggle is still positioned within the inspector
   panel's rect (assert containment), and does not intersect the delete
   button.
5. Retained light and dark screenshots of the narrow expanded state.

Then re-run these tied suites **unmodified** and report their output:

```
.loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
.loom/tied/04-named-section-dividers/verify_named_dividers.py
.loom/tied/05-compact-chrome/verify_compact_chrome.py
.loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
.loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
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

If the venv is missing: `python3 -m venv ~/.venvs/bopos && ~/.venvs/bopos/bin/pip
install -r dashboard/requirements.txt pyOSC3 playwright && ~/.venvs/bopos/bin/playwright
install chromium --only-shell`.

## Deliverables in the stitch directory

- `verify_inspector_toggle_overlap.py`
- `verification.md` — the exact commands run and their real output tails, plus
  the confirmed root cause and any deviation from this spec, with reasoning.
- retained screenshots.

## Acceptance checks (run them; paste real output, do not summarize away failures)

```sh
cd /Users/bob/repos/bopOS
~/.venvs/bopos/bin/python .loom/threads/19-show-chrome-fixes/01-inspector-toggle-overlap.stitching/verify_inspector_toggle_overlap.py
~/.venvs/bopos/bin/python .loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
~/.venvs/bopos/bin/python .loom/tied/04-named-section-dividers/verify_named_dividers.py
~/.venvs/bopos/bin/python .loom/tied/05-compact-chrome/verify_compact_chrome.py
~/.venvs/bopos/bin/python .loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
~/.venvs/bopos/bin/python .loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
git checkout -- .loom/tied/
```

Every suite must end `0 failure(s)`. If a tied suite asserts something this
fix legitimately changes, STOP and report the exact assertion — do not edit a
tied suite. Do not commit; leave the working tree for the orchestrator to
review. Report: what changed (diff summary), how verified (real output), and
anything you could not do.
