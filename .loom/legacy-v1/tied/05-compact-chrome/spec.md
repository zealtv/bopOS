# Implementation spec — compact chrome, Show tab only (stitch 05)

Repo: /Users/bob/repos/bopOS. Read first: `instructions.md` and
`decisions.md` in this stitch directory (decisions.md carries the ruled
scope and the concrete values — use those values), `/Users/bob/repos/bopOS/CLAUDE.md`,
and skim `.loom/tied/01-layout-review/wireframes.html` for the intended
feel (sharper corners, buttons wrapping tightly around their text,
compact rows).

Work ONLY on:
- `dashboard/static/css/style.css`
- a new verifier `verify_compact_chrome.py` in this stitch directory

No JS changes expected (this is a chrome pass; if you believe a JS change
is required, STOP and report why instead of making it). Do not touch loom
state, `.pd` files, `facilitator.*`, index.html.

## The pass

1. Add the `--chrome-*` variables from decisions.md to the FIRST `:root`
   block (they are theme-independent; do not duplicate into the
   light/dark/data-theme blocks).
2. Rewrite the Show-tab rules ONLY (`.show-*`, `#show-consoles`,
   `#show-wire-preview`, the Show sections of style.css) to consume them:
   - panel/console/transport-strip/inspector radii 9px → `var(--chrome-radius-panel)`
   - button/input/select/row radii 5–7px → `var(--chrome-radius-control)`
   - pill/chip/tiny radii → `var(--chrome-radius-small)` (target-chip stays
     pill-shaped: keep its 15px rounding — it's a deliberate shape, not chrome)
   - control min-heights 44px → `var(--chrome-control-height)` on Show-tab
     buttons/inputs/selects; button paddings → `var(--chrome-control-pad)`
   - panel paddings 16px → `var(--chrome-panel-pad)`; workspace/console
     gaps and `#show-consoles` margin 18px → `var(--chrome-gap)`; adjust
     `.show-workspace` right padding for the new gap (300px + gap, 40px + gap)
   - console summary/bar/log paddings and margins tightened to match
   - the rows scrollbox (`.show-rows-box`) gets a visible border
     (`1px solid var(--line)`, `var(--chrome-radius-control)`) so the
     bound reads clearly; edit bar above it unchanged in structure
3. Touch safety: any control that a finger uses (edit-bar buttons,
   transport buttons, step-row transport, toggle/rail, console summary,
   inspector buttons/inputs on touch layouts) must keep an effective
   ≥44px hit target. The house pattern is `::after{inset:-Npx}` — extend
   insets where the visual shrink would drop the effective box below
   44px. Inputs/selects (no ::after possible on all of them) may keep
   a taller min-height at ≤760px via the existing mobile media block.
4. Keyboard `:focus-visible` outlines must remain visible on every
   changed control (the global rule exists; don't clip it with
   overflow/inset changes).
5. Do NOT touch: non-Show tabs' rules, facilitator.css, pill colour
   classes, spatial styles, the `::details-content` console mechanics,
   the container-query blocks' logic (update only px values inside Show
   rules), animations.

## Sanity constraint

The stitch must not change layout semantics: same elements, same
stacking, same responsive breakpoints (900px consoles, 1020px sidebar,
760px stacking). It is a values pass through variables.

## Verifier

`verify_compact_chrome.py`, conventions from
`.loom/tied/04-named-section-dividers/verify_named_dividers.py` (repo
root by marker, non-default ports, real server + simfleet, teardown,
screenshots retained here). Run with `~/.venvs/bopos/bin/python`. Cover
at least:

- computed-style assertions on representative controls: an edit-bar
  button, a step row, the inspector panel, a console, an inspector input
  — border-radius and min-height/padding match the decisions.md values
  (read `getComputedStyle`, compare px)
- the `:root` variables resolve (getComputedStyle on documentElement)
- edit bar pinned above the rows box; rows box scrolls (bounded) and has
  a visible border
- effective hit targets at 768px: for each touch-relevant control class,
  visual box + ::after expansion ≥ 44px in both axes (compute via
  getComputedStyle of the pseudo-element insets)
- `:focus-visible` outline still present on a focused edit-bar button
  (focus via keyboard, read computed outline-width ≠ 0)
- light and dark screenshots of the Show tab at 1280px and 768px,
  retained in this directory
- no page-level horizontal overflow at 1280px and 768px
- re-run UNMODIFIED: `.loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py`,
  `.loom/tied/04-named-section-dividers/verify_named_dividers.py`,
  `.loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py`,
  `.loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py`
  — then restore their screenshot artifacts with `git checkout -- .loom/tied/`.

Playwright house rules (generalize): elements in non-active tab panels
need `state="attached"`; no actionability/stability waits or
`scroll_into_view_if_needed` (heartbeat re-renders + CSS animation) —
one-shot `page.evaluate` scrolls and fresh `bounding_box()`; compared
rects gathered in one `page.evaluate`; one type-aware dialog handler;
`wait_for_function(expr, arg=value)`; `inner_text` applies
`text-transform`.

## Acceptance checks (run them; report real output)

```sh
cd <repo-root>
~/.venvs/bopos/bin/python .loom/threads/18-show-chrome-density/05-compact-chrome.stitching/verify_compact_chrome.py
~/.venvs/bopos/bin/python .loom/tied/02-inspector-sidebar/verify_inspector_sidebar.py
~/.venvs/bopos/bin/python .loom/tied/04-named-section-dividers/verify_named_dividers.py
~/.venvs/bopos/bin/python .loom/tied/02-edit-bar-and-inline-step-name/verify_edit_bar.py
~/.venvs/bopos/bin/python .loom/tied/03-responsive-osc-terminals/verify_osc_terminals.py
```

All must end `0 failure(s)`. NOTE: tied suites assert behavior/layout,
not exact px chrome — if one of them asserts a concrete value this pass
changes (e.g. a fixed 44px min-height or 300px+18px offset arithmetic),
STOP and report the exact assertion instead of modifying the tied suite
or contorting the chrome. Exception already known: the 02 sidebar suite
computes workspace padding from the DOM, not constants, so gap changes
should be safe — verify. Summarize what changed, how verified, and
anything you could not do — explicitly, no faked results.
