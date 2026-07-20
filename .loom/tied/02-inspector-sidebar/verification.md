# Verification — 02-inspector-sidebar

Implementation delegated to an Opus 4.8 sub-agent against `spec.md` (codex
unavailable this session — weekly budget spent). Orchestrator reviewed the
full diff and independently re-ran every suite from `~/.venvs/bopos`
(2026-07-21):

- `verify_inspector_sidebar.py` — **0 failures** (22 checks): consoles/list
  rects stable while the inspector grows and scrolls internally;
  collapse/expand width reclaim + round-trip; state survives re-render,
  reload resets to expanded; collapsed single-click selects silently,
  double-click (step row / message pill) expands onto the item; keyboard
  toggle + aria-expanded; no horizontal overflow at 1280px (both states)
  and 768px; light/dark screenshots retained in this directory.
- `.loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py`
  unmodified — **0 failures**.
- `.loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py`
  unmodified — **0 failures**. (Both tied suites overwrite their retained
  screenshots on re-run; restored via `git checkout -- .loom/tied/`.)

Non-obvious implementation fact (recorded for future sessions): native
`dblclick` never fires on Show rows/pills — the first click's `setFocus()`
re-render replaces the DOM node, so the two clicks hit different nodes.
The double-click-to-expand ruling is implemented as manual same-uid <400ms
detection inside the click handler.

Footprint mechanism: `.show-workspace` is `position:relative` +
right-padding; the `aside` is absolutely positioned (out of flow) with a
sticky, viewport-capped, internally scrolling `.show-inspector-panel`
inside; the container query stays on the width-owning shell. ≤1020px
reverts to the static single-column layout.
