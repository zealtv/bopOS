# Task: Show-tab step-list scroll box, stable add bar, console default heights

Repo: /Users/bob/repos/bopOS. Files: `dashboard/static/js/show.js`,
`dashboard/static/css/style.css`, one new verify script. Never touch `.pd`
files or `.loom` state (write only into the stitch directory named below).

## Background

The Show tab (`renderLoadedShow` in show.js) renders `.show-rows` (step +
divider rows) with the `.show-add-bar` (+ Step / + Divider) directly below,
inside a two-column `.show-workspace` grid next to the inspector. Long shows
currently grow the page; the add bar drifts down with content. Below the
workspace, stitch-7's OSC consoles are `<details class="show-console">`
elements created once at startup (outside `#show-root`, never re-rendered).
p1–p3 are already applied: exclusive playback, optimistic transport, global
transport strip; re-renders happen on broadcasts and a 500 ms countdown
tick, and `render()` carries uncommitted form state (shows dropdown, cue
lead) across rebuilds.

## Change 1 — vertically resizable scroll box

Wrap the step rows (only the rows — not the add bar) in a
`.show-rows-box` container: default height that fits roughly 14 compact
rows (~34 px each ≈ 480 px; pick the exact value against the 5b dense
layout and log it), `overflow-y: auto`, `overscroll-behavior: contain`,
visible empty space below the last row (the container keeps its height
when content is shorter). Make it user-resizable vertically with native
CSS `resize: vertical` — BUT native resize handles are unusable on touch,
and the house verifies run `has_touch=True, is_mobile=True` at 768×1024:
so also add a slim full-width drag handle bar (`.show-rows-resize`,
~10 px, `touch-action: none`) beneath the box that adjusts the box height
via pointer events (pointerdown/move/up with setPointerCapture). The
chosen height must survive re-renders (store it in a module-level
variable applied inline on rebuild; do not persist it server-side).
Log in your report which of native/custom carries which environment.

**Critical re-render constraint**: the whole Show tab re-renders every
500 ms while a step plays. The box's scroll position AND height must be
carried across `render()` rebuilds (same pattern as the existing
uncommitted-pick guard: read before rebuild, re-apply after). A drag in
progress must not be broken by a rebuild (the handle element is replaced;
re-acquire in the pointermove or gate rebuild application while dragging —
simplest correct approach wins; document it).

## Change 2 — add bar stays put

`.show-add-bar` sits outside/below the scroll box (plus the resize
handle), so its y-position is independent of step count. After clicking
"+ Step", the new step must be scrolled into view inside the box (the
add flow already focuses the created step via the server round-trip;
scroll the focused row into view on the render that introduces it —
`scrollIntoView({block: "nearest"})` on the row when it first appears is
enough; don't yank the box on every render).

## Change 3 — console default heights

On first paint the consoles must match stitch-7's intended default:
both `<details>` collapsed (no `open` attribute) and the log area at its
default `max-height: 240px`. Inspect the current startup path for
anything that reopens or resizes them on load (e.g. a stray `open`
attribute, a persisted toggle, or the first `renderConsole` forcing a
scroll) and make first load deterministic: collapsed summaries, default
heights, counters at zero. Toggling and the pause/clear/filter controls
keep working exactly as now. If investigation shows they already start
collapsed and the bug is something adjacent (e.g. the summary count
painting "0 shown · 0 seen" oddly), report what you found and fix the
actual first-paint defect you can demonstrate; do not invent one.

## Change 4 — budgets hold

No page-level horizontal scroll at 768×1024 or ≤760 px; the 5b dense
budget still passes. On the ≤760 px single-column layout the scroll box
and handle must remain usable (full-width).

CSS edits go into the existing one-line show blocks in place — no
`!important`, no appended override blocks.

## Verify script (new)

`.loom/threads/15-show-polish/p4-step-list-scrollbox.stitching/verify_show_scrollbox.py`
— house pattern (copy the harness from
`.loom/tied/p3-global-transport-and-cue-lead/verify_show_transport.py`):
repo root by marker, random ports, real server + simfleet, headless
Chromium (`has_touch=True, is_mobile=True`, 900×1100 or the 5b 768×1024 —
match the tied suites), one type-aware dialog handler, teardown, `check()`
lines, exit 1 on failure. Fixture: a show with 30 steps.

Checks:

1. The rows box scrolls internally (scrollHeight > clientHeight) while
   the add bar and transport strip are both fully inside the viewport.
2. Read the add bar's bounding-box y; click "+ Step"; after the
   round-trip the add bar's y is unchanged and the new (focused) step row
   is visible inside the box (its rect within the box's rect).
3. Drag the resize handle down ~120 px with touch/pointer events; the
   box's clientHeight grows accordingly; a later render tick (start a
   step playing, wait >600 ms) preserves the resized height and the
   scroll position.
4. Consoles on a fresh page load: both `details` not open; toggling one
   open shows the log at default height; reloading the page shows them
   collapsed again.
5. `document.documentElement.scrollWidth <= window.innerWidth` (no page
   horizontal scroll) at the test viewport.
6. No page errors.

## Acceptance checks (run these; all must pass)

```sh
~/.venvs/bopos/bin/python .loom/threads/15-show-polish/p4-step-list-scrollbox.stitching/verify_show_scrollbox.py
~/.venvs/bopos/bin/python .loom/tied/p1-zero-value-and-transport-bugs/verify_show_polish_bugs.py
~/.venvs/bopos/bin/python .loom/tied/p2-exclusive-playback-and-progress/verify_show_exclusive.py
~/.venvs/bopos/bin/python .loom/tied/p3-global-transport-and-cue-lead/verify_show_transport.py
~/.venvs/bopos/bin/python .loom/tied/4-tab-ui/verify_show_tab.py
~/.venvs/bopos/bin/python .loom/tied/5-inspector/verify_show_inspector.py
~/.venvs/bopos/bin/python .loom/tied/5b-compact-rows/verify_show_compact.py
~/.venvs/bopos/bin/python .loom/tied/5c-target-model-and-picker/verify_show_targets.py
~/.venvs/bopos/bin/python .loom/tied/6-message-editing/verify_show_editing.py
~/.venvs/bopos/bin/python .loom/tied/6b-show-management/verify_show_management.py
```

Tied suites that measure the rows' container geometry may need minimal
amendments for the new box — amend and list each in your report. Restore
any regenerated screenshot files. Any other failure is a regression in
your change: fix the change, not the test.

Do not commit. Write a report to
`.loom/threads/15-show-polish/p4-step-list-scrollbox.stitching/codex-report.md`:
what changed per change-number, the default-height and touch-resize
decisions, what change 3's investigation actually found, tied amendments,
verify output, anything not done. If you could not complete the task, say
so explicitly.
